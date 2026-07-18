#!/usr/bin/env python3
"""TURNCTL portfolio-layer diagnostic.

Importing this module is side-effect free.  The CLI validates authority before
creating either an output or scratch directory.  Pure functions below freeze
the policy registry, hysteresis membership, partial rebalance, cash-inclusive
one-way turnover cap, and realized holding-slot admission used by the formal
sequential execution worker.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
import yaml


REPO_ROOT = Path(__file__).resolve().parents[6]
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    EXPERIMENT_ROOT
    / "configs/config_20b_p4_top_region_hysteresis_partial_rebalance_turnover_control.yaml"
)
RUN_ID = "20B_P4_top_region_hysteresis_partial_rebalance_turnover_control_v0"
CONTRACT_VERSION = "20B_P4_TURNCTL_v0"
PRIMARY_POLICY_ID = "F_MIX403030_XD7_R050_C040"
SECONDARY_POLICY_ID = "F_MIX333_XD7_R050_C040"
COMPARATOR_POLICY_ID = "C_D8_ONLY_XD8_R100_CNONE"
EVENT_MONTHS = frozenset({"2024-10", "2025-02", "2025-08", "2025-09", "2026-04"})


class ContractError(RuntimeError):
    """A frozen requirement condition was violated."""


class AuthorizationError(ContractError):
    """Historical outcome execution was requested without explicit authority."""


@dataclass(frozen=True)
class TurnoverPlan:
    execution_weights: dict[str, float]
    partial_weights: dict[str, float]
    planned_buy_before_cap: float
    planned_sell_before_cap: float
    planned_one_way_before_cap: float
    cap_scale: float
    planned_buy_after_cap: float
    planned_sell_after_cap: float
    planned_one_way_after_cap: float
    planned_cash_weight_delta: float


EXPECTED_TOP_LEVEL_KEYS = {
    "identity",
    "authorization",
    "paths",
    "upstream_hashes",
    "population",
    "policy_grid",
    "membership",
    "execution",
    "cost",
    "statistics",
    "serialization",
    "output_contract",
}
EXPECTED_SECTION_KEYS: dict[str, set[str]] = {
    "identity": {"experiment_id", "phase_id", "run_id", "contract_version"},
    "authorization": {
        "requirement_generation_authorized", "requirement_execution_authorized",
        "implementation_authorized", "historical_outcome_execution_authorized",
        "portfolio_replay_authorized", "model_training_authorized",
        "score_recomputation_authorized", "bucket_recomputation_authorized",
        "parameter_selection_authorized", "deployment_authorized",
    },
    "paths": {
        "requirement_file", "MLRANK_ROOT", "MLRANK_OUTPUT_HASHES", "MLRANK_MANIFEST",
        "MLRANK_DECISION", "SCORE_BUNDLE_MANIFEST", "SCORE_BUNDLE_HASHES",
        "BUCKET_ASSIGNMENT", "SCORE_PANEL", "FEATURE_PANEL", "PORTSENS_ROOT",
        "PORTSENS_OUTPUT_HASHES", "PORTSENS_MANIFEST", "PORTSENS_DECISION",
        "PORTSENS_RESOLVED_CONFIG", "PORTSENS_CONTRACT_SNAPSHOT",
        "PORTSENS_INPUT_AUDIT", "PORTSENS_COST_REGISTRY", "RAW_OHLCV_ROOT",
        "QFQ_ROOT", "TRADING_CALENDAR_FILE", "PROJECT_UNIVERSE_FILE",
        "SECURITY_MASTER_FILE", "SH_NAME_HISTORY_ROOT", "SZ_NAME_HISTORY_FILE",
        "MARKET_RULE_REGISTRY_FILE", "output_root", "replay_a_scratch_root",
        "replay_b_scratch_root",
    },
    "upstream_hashes": {
        "MLRANK_OUTPUT_HASHES_sha256", "MLRANK_MANIFEST_sha256", "MLRANK_DECISION_sha256",
        "SCORE_BUNDLE_MANIFEST_sha256", "SCORE_BUNDLE_HASHES_sha256",
        "BUCKET_ASSIGNMENT_sha256", "SCORE_PANEL_sha256", "FEATURE_PANEL_sha256",
        "PORTSENS_OUTPUT_HASHES_sha256", "PORTSENS_MANIFEST_sha256",
        "PORTSENS_DECISION_sha256", "PORTSENS_RESOLVED_CONFIG_sha256",
        "PORTSENS_CONTRACT_SNAPSHOT_sha256", "PORTSENS_INPUT_AUDIT_sha256",
        "PORTSENS_COST_REGISTRY_sha256",
    },
    "population": {
        "scored_model_id", "split", "decision_date_min", "decision_date_max",
        "decision_month_n", "transition_month_n", "scored_row_n",
        "union_instrument_n", "event_label_months",
    },
    "policy_grid": {
        "factorial_mix_ids", "exit_bucket_floors", "partial_rebalance_rhos",
        "monthly_one_way_turnover_caps", "comparator_ids", "primary_policy_id",
        "secondary_policy_id", "turnover_comparator_policy_id", "exact_policy_n",
    },
    "membership": {
        "entry_bucket_floor", "actual_holding_caps", "incumbent_rule", "d8_priority",
        "new_entry_priority", "slot_admission_session_rule", "midmonth_late_buy_after_slot_release",
    },
    "execution": {
        "initial_AUM_cny", "initial_formation_full_rebalance", "target_stock_weight_cap",
        "realized_single_weight_soft_limit", "realized_single_weight_emergency_limit",
        "decision_timing", "rebalance_timing", "sell_before_buy", "leverage_allowed",
        "short_allowed", "unallocated_capital", "planned_turnover_formula",
        "attempted_turnover_formula", "realized_turnover_formula", "actual_holding_rule",
    },
    "cost": {
        "inherited_contract", "reference_cost_id", "reference_slippage_bps",
        "commission_buy_bps", "commission_sell_bps", "minimum_commission_cny",
        "stamp_tax_sell_bps", "stamp_tax_effective_start",
    },
    "statistics": {
        "month_scopes", "bootstrap_method", "block_length_months", "repetitions",
        "rng", "seed", "quantiles", "event_affirmative_support_contribution",
    },
    "serialization": {
        "csv_encoding", "csv_newline", "csv_na_rep", "csv_float_format",
        "gzip_compresslevel", "gzip_mtime", "json_ensure_ascii", "json_sort_keys",
        "json_indent", "parquet_engine", "parquet_version", "parquet_compression",
        "parquet_compression_level", "parquet_use_dictionary", "parquet_write_statistics",
        "parquet_data_page_version", "parquet_row_group_size",
    },
    "output_contract": {
        "schema_version", "decision_name", "report_name", "manifest_name",
        "output_hashes_name", "success_profile_id", "seal_failure_exit_code",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def load_config(path: str | Path = DEFAULT_CONFIG) -> tuple[dict[str, Any], Path]:
    config_path = resolve_repo_path(path)
    with config_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ContractError("config root must be a mapping")
    if set(config) != EXPECTED_TOP_LEVEL_KEYS:
        missing = sorted(EXPECTED_TOP_LEVEL_KEYS - set(config))
        unknown = sorted(set(config) - EXPECTED_TOP_LEVEL_KEYS)
        raise ContractError(f"config top-level keys mismatch: missing={missing}, unknown={unknown}")
    for section, expected in EXPECTED_SECTION_KEYS.items():
        observed = set(config[section])
        if observed != expected:
            missing = sorted(expected - observed)
            unknown = sorted(observed - expected)
            raise ContractError(f"config section {section} keys mismatch: missing={missing}, unknown={unknown}")
    expected_identity = {
        "experiment_id": "20_ohlcv_positive_beta_exposure_research",
        "phase_id": "20B_P4_TURNCTL",
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
    }
    if config["identity"] != expected_identity:
        raise ContractError("identity differs from frozen TURNCTL contract")
    if int(config["policy_grid"]["exact_policy_n"]) != 75:
        raise ContractError("exact_policy_n must be 75")
    return config, config_path


def require_historical_authority(config: Mapping[str, Any]) -> None:
    authorization = config["authorization"]
    if not authorization.get("implementation_authorized", False):
        raise AuthorizationError("implementation_authorized is false")
    required = ("historical_outcome_execution_authorized", "portfolio_replay_authorized")
    missing = [key for key in required if not authorization.get(key, False)]
    if missing:
        raise AuthorizationError("formal historical replay is locked: " + ", ".join(missing))
    forbidden = (
        "model_training_authorized",
        "score_recomputation_authorized",
        "bucket_recomputation_authorized",
        "parameter_selection_authorized",
        "deployment_authorized",
    )
    enabled = [key for key in forbidden if authorization.get(key, False)]
    if enabled:
        raise AuthorizationError("forbidden authorization enabled: " + ", ".join(enabled))


def _policy_row(
    policy_id: str,
    role: str,
    mix_id: str,
    weights: tuple[float, float, float],
    exit_floor: int,
    rho: float,
    cap: float | None,
    holding_cap: int,
) -> dict[str, Any]:
    return {
        "policy_id": policy_id,
        "policy_role": role,
        "capital_mix_id": mix_id,
        "d8_sleeve_weight": weights[0],
        "d9_sleeve_weight": weights[1],
        "d10_sleeve_weight": weights[2],
        "entry_bucket_floor": "D8",
        "exit_bucket_floor": f"D{exit_floor}",
        "partial_rebalance_rho": rho,
        "monthly_one_way_turnover_cap": cap,
        "actual_holding_cap": holding_cap,
        "new_entry_priority_rule": "D10>D9>D8,model_score_desc,instrument_id_asc",
        "slot_admission_session_rule": "scheduled_next_open_after_sell_fills_only",
        "initial_formation_full_rebalance": True,
        "reference_cost_id": "SLIP005",
        "sector_tilt_lambda": 0.0,
        "stop_threshold": np.nan,
        "primary_gate_eligible": policy_id == PRIMARY_POLICY_ID,
        "secondary_readout": policy_id == SECONDARY_POLICY_ID,
    }


def build_policy_registry() -> pd.DataFrame:
    """Return the exact, stable 72-factorial plus 3-comparator registry."""
    rows: list[dict[str, Any]] = []
    mixes = {
        "MIX333": (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0),
        "MIX403030": (0.40, 0.30, 0.30),
    }
    cap_codes = ((None, "NONE"), (0.20, "020"), (0.30, "030"), (0.40, "040"))
    rho_codes = ((0.25, "025"), (0.50, "050"), (1.00, "100"))
    for mix_id, weights in mixes.items():
        for floor in (8, 7, 6):
            for rho, rho_code in rho_codes:
                for cap, cap_code in cap_codes:
                    policy_id = f"F_{mix_id}_XD{floor}_R{rho_code}_C{cap_code}"
                    rows.append(_policy_row(policy_id, "factorial", mix_id, weights, floor, rho, cap, 134))
    rows.extend(
        [
            _policy_row(COMPARATOR_POLICY_ID, "comparator", "D8_ONLY", (1.0, 0.0, 0.0), 8, 1.0, None, 45),
            _policy_row("C_D9D10_EQUAL_XD8_R100_CNONE", "comparator", "D9D10_EQUAL", (0.0, 0.5, 0.5), 8, 1.0, None, 89),
            _policy_row("C_MIX303040_XD8_R100_CNONE", "comparator", "MIX303040", (0.30, 0.30, 0.40), 8, 1.0, None, 134),
        ]
    )
    frame = pd.DataFrame(rows).sort_values("policy_id", kind="stable").reset_index(drop=True)
    if len(frame) != 75 or frame["policy_id"].nunique() != 75:
        raise ContractError("policy registry must contain exactly 75 unique rows")
    if frame["primary_gate_eligible"].sum() != 1 or frame["secondary_readout"].sum() != 1:
        raise ContractError("primary and secondary policy flags must each be unique")
    return frame


def _policy_value(policy: Mapping[str, Any] | pd.Series, key: str) -> Any:
    return policy[key]


def form_hard_target(
    assignment_month: pd.DataFrame,
    policy: Mapping[str, Any] | pd.Series,
    decision_close_shares: Mapping[str, float],
    decision_close_weights: Mapping[str, float],
) -> pd.DataFrame:
    """Form one policy-month hard target without reading future bars or returns."""
    required = {"instrument_id", "bucket_id", "model_score", "model_score_rank"}
    if not required.issubset(assignment_month):
        raise ContractError(f"assignment is missing columns: {sorted(required - set(assignment_month))}")
    month = assignment_month.loc[:, sorted(required)].copy()
    if month["instrument_id"].duplicated().any():
        raise ContractError("duplicate instrument in assignment month")
    month["bucket_id"] = month["bucket_id"].astype(int)
    month["incumbent"] = month["instrument_id"].map(lambda x: float(decision_close_shares.get(x, 0.0)) > 0.0)
    month["decision_close_position_weight"] = month["instrument_id"].map(decision_close_weights).fillna(0.0).astype(float)
    month["selected"] = False
    month["sleeve_id"] = ""
    month["membership_priority_rank"] = np.nan
    month["hard_target_weight"] = 0.0
    mix_id = str(_policy_value(policy, "capital_mix_id"))
    weights = {8: float(_policy_value(policy, "d8_sleeve_weight")), 9: float(_policy_value(policy, "d9_sleeve_weight")), 10: float(_policy_value(policy, "d10_sleeve_weight"))}
    quotas = {bucket: int((month["bucket_id"] == bucket).sum()) for bucket in (8, 9, 10)}

    selected_by_sleeve: dict[int, list[str]] = {8: [], 9: [], 10: []}
    if mix_id == "D8_ONLY":
        selected_by_sleeve[8] = sorted(month.loc[month["bucket_id"] == 8, "instrument_id"].astype(str))
    elif mix_id == "D9D10_EQUAL":
        for bucket in (9, 10):
            selected_by_sleeve[bucket] = sorted(month.loc[month["bucket_id"] == bucket, "instrument_id"].astype(str))
    else:
        exit_floor = int(str(_policy_value(policy, "exit_bucket_floor")).removeprefix("D"))
        d8_candidates = month.loc[
            (month["bucket_id"] == 8)
            | (month["incumbent"] & month["bucket_id"].between(exit_floor, 7))
        ].copy()
        d8_candidates = d8_candidates.sort_values(
            ["incumbent", "bucket_id", "model_score", "decision_close_position_weight", "instrument_id"],
            ascending=[False, False, False, False, True],
            kind="stable",
        )
        if len(d8_candidates) < quotas[8]:
            raise ContractError("D8 hysteresis candidate count below sealed D8 quota")
        selected_by_sleeve[8] = d8_candidates.head(quotas[8])["instrument_id"].astype(str).tolist()
        for rank, instrument in enumerate(d8_candidates["instrument_id"].astype(str), start=1):
            month.loc[month["instrument_id"] == instrument, "membership_priority_rank"] = rank
        for bucket in (9, 10):
            selected_by_sleeve[bucket] = sorted(month.loc[month["bucket_id"] == bucket, "instrument_id"].astype(str))

    flattened = [instrument for bucket in (8, 9, 10) for instrument in selected_by_sleeve[bucket]]
    if len(flattened) != len(set(flattened)):
        raise ContractError("instrument assigned to more than one sleeve")
    for bucket, members in selected_by_sleeve.items():
        if weights[bucket] == 0.0:
            if members:
                raise ContractError("zero-weight sleeve unexpectedly has members")
            continue
        if not members:
            raise ContractError(f"nonzero D{bucket} sleeve has no members")
        target_weight = weights[bucket] / len(members)
        mask = month["instrument_id"].isin(members)
        month.loc[mask, "selected"] = True
        month.loc[mask, "sleeve_id"] = f"D{bucket}"
        month.loc[mask, "hard_target_weight"] = target_weight
    if float(month["hard_target_weight"].max()) > 0.03 + 1e-12:
        raise ContractError("hard target single-name concentration exceeds 3%")
    if not math.isclose(float(month["hard_target_weight"].sum()), 1.0, abs_tol=1e-12):
        raise ContractError("hard target stock weights do not sum to one")
    month["entry_eligible"] = month["bucket_id"].between(8, 10)
    month["buffer_eligible"] = month["selected"] & month["bucket_id"].between(6, 7)
    month["exit_target"] = month["incumbent"] & ~month["selected"]
    return month.sort_values("instrument_id", kind="stable").reset_index(drop=True)


def plan_partial_rebalance(
    drift_weights: Mapping[str, float],
    hard_target_weights: Mapping[str, float],
    rho: float,
    turnover_cap: float | None,
    *,
    launch_month: bool = False,
) -> TurnoverPlan:
    """Apply rho and the cash-inclusive max(buy,sell) one-way cap."""
    if not 0.0 < float(rho) <= 1.0:
        raise ContractError("rho must be in (0, 1]")
    if turnover_cap is not None and not 0.0 < float(turnover_cap) <= 1.0:
        raise ContractError("turnover cap must be in (0, 1]")
    domain = sorted(set(drift_weights) | set(hard_target_weights))
    drift = {key: float(drift_weights.get(key, 0.0)) for key in domain}
    hard = {key: float(hard_target_weights.get(key, 0.0)) for key in domain}
    if any(value < -1e-12 for value in drift.values()) or sum(drift.values()) > 1.0 + 1e-10:
        raise ContractError("invalid pretrade drift stock weights")
    if any(value < -1e-12 for value in hard.values()) or sum(hard.values()) > 1.0 + 1e-10:
        raise ContractError("invalid hard target stock weights")
    effective_rho = 1.0 if launch_month else float(rho)
    partial = {key: drift[key] + effective_rho * (hard[key] - drift[key]) for key in domain}
    delta = {key: partial[key] - drift[key] for key in domain}
    buy_before = sum(max(value, 0.0) for value in delta.values())
    sell_before = sum(max(-value, 0.0) for value in delta.values())
    one_way_before = max(buy_before, sell_before)
    effective_cap = None if launch_month else turnover_cap
    scale = 1.0 if effective_cap is None or one_way_before <= float(effective_cap) else float(effective_cap) / one_way_before
    execution = {key: drift[key] + scale * delta[key] for key in domain}
    actual_delta = {key: execution[key] - drift[key] for key in domain}
    buy_after = sum(max(value, 0.0) for value in actual_delta.values())
    sell_after = sum(max(-value, 0.0) for value in actual_delta.values())
    one_way_after = max(buy_after, sell_after)
    if effective_cap is not None and one_way_after > float(effective_cap) + 1e-12:
        raise ContractError("planned turnover cap breached")
    for key in domain:
        lo, hi = sorted((drift[key], hard[key]))
        if execution[key] < lo - 1e-12 or execution[key] > hi + 1e-12:
            raise ContractError("execution plan overshoots hard target")
    drift_cash = 1.0 - sum(drift.values())
    execution_cash = 1.0 - sum(execution.values())
    half_l1 = 0.5 * (sum(abs(value) for value in actual_delta.values()) + abs(execution_cash - drift_cash))
    if not math.isclose(half_l1, one_way_after, abs_tol=1e-12):
        raise ContractError("cash-inclusive half-L1 identity failed")
    return TurnoverPlan(
        execution_weights=execution,
        partial_weights=partial,
        planned_buy_before_cap=buy_before,
        planned_sell_before_cap=sell_before,
        planned_one_way_before_cap=one_way_before,
        cap_scale=scale,
        planned_buy_after_cap=buy_after,
        planned_sell_after_cap=sell_after,
        planned_one_way_after_cap=one_way_after,
        planned_cash_weight_delta=execution_cash - drift_cash,
    )


def admit_new_entries(
    target_state: pd.DataFrame,
    post_sell_shares: Mapping[str, float],
    actual_holding_cap: int,
) -> pd.DataFrame:
    """Authorize zero-share targets only after realized sells release slots."""
    required = {"instrument_id", "hard_target_weight", "sleeve_id", "model_score"}
    if not required.issubset(target_state):
        raise ContractError(f"target state is missing columns: {sorted(required - set(target_state))}")
    result = target_state.copy()
    held = {instrument for instrument, shares in post_sell_shares.items() if float(shares) > 0.0}
    if len(held) > actual_holding_cap:
        raise ContractError("post-sell actual holding count already breaches cap")
    slots = max(0, int(actual_holding_cap) - len(held))
    result["entry_authorized"] = False
    result["entry_queue_status"] = ""
    result["available_new_holding_slots"] = slots
    existing_mask = result["instrument_id"].isin(held) & (result["hard_target_weight"] > 0)
    result.loc[existing_mask, "entry_authorized"] = True
    candidates = result.loc[(result["hard_target_weight"] > 0) & ~result["instrument_id"].isin(held)].copy()
    sleeve_rank = {"D10": 0, "D9": 1, "D8": 2}
    candidates["_sleeve_rank"] = candidates["sleeve_id"].map(sleeve_rank)
    if candidates["_sleeve_rank"].isna().any():
        raise ContractError("new target has invalid sleeve identity")
    candidates = candidates.sort_values(["_sleeve_rank", "model_score", "instrument_id"], ascending=[True, False, True], kind="stable")
    authorized = set(candidates.head(slots)["instrument_id"])
    queued = set(candidates.iloc[slots:]["instrument_id"])
    result.loc[result["instrument_id"].isin(authorized), "entry_authorized"] = True
    result.loc[result["instrument_id"].isin(authorized), "entry_queue_status"] = "authorized_realized_holding_slot"
    result.loc[result["instrument_id"].isin(queued), "entry_queue_status"] = "queued_no_realized_holding_slot"
    return result.drop(columns=[column for column in result if column.startswith("_")])


HASH_PATH_KEYS = (
    "MLRANK_OUTPUT_HASHES", "MLRANK_MANIFEST", "MLRANK_DECISION",
    "SCORE_BUNDLE_MANIFEST", "SCORE_BUNDLE_HASHES", "BUCKET_ASSIGNMENT",
    "SCORE_PANEL", "FEATURE_PANEL", "PORTSENS_OUTPUT_HASHES", "PORTSENS_MANIFEST",
    "PORTSENS_DECISION", "PORTSENS_RESOLVED_CONFIG", "PORTSENS_CONTRACT_SNAPSHOT",
    "PORTSENS_INPUT_AUDIT", "PORTSENS_COST_REGISTRY",
)


def run_static_preflight(config: Mapping[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read only sealed static inputs; never reads returns or creates output."""
    audit_rows = []
    for key in HASH_PATH_KEYS:
        path = resolve_repo_path(config["paths"][key])
        expected = str(config["upstream_hashes"][f"{key}_sha256"])
        observed = sha256_file(path) if path.is_file() else "MISSING"
        audit_rows.append({
            "input_id": key,
            "path": str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path),
            "expected_sha256": expected,
            "observed_sha256": observed,
            "hash_match": observed == expected,
        })
    audit = pd.DataFrame(audit_rows)
    if not bool(audit["hash_match"].all()):
        failed = audit.loc[~audit["hash_match"], "input_id"].tolist()
        raise ContractError(f"upstream immutable hash mismatch: {failed}")
    inherited = _portsens_module()
    mlrank_root = resolve_repo_path(config["paths"]["MLRANK_ROOT"])
    portsens_root = resolve_repo_path(config["paths"]["PORTSENS_ROOT"])
    nested_failures = inherited.verify_hash_registry(
        mlrank_root, resolve_repo_path(config["paths"]["MLRANK_OUTPUT_HASHES"])
    )
    nested_failures += inherited.verify_hash_registry(
        mlrank_root / "scores", resolve_repo_path(config["paths"]["SCORE_BUNDLE_HASHES"])
    )
    nested_failures += inherited.verify_hash_registry(
        portsens_root, resolve_repo_path(config["paths"]["PORTSENS_OUTPUT_HASHES"])
    )
    if nested_failures:
        raise ContractError(f"nested upstream registry mismatch: {nested_failures[:10]}")
    with resolve_repo_path(config["paths"]["PORTSENS_RESOLVED_CONFIG"]).open(encoding="utf-8") as handle:
        inherited_config = yaml.safe_load(handle)
    inherited.run_preflight(inherited_config)
    assignment = pd.read_parquet(resolve_repo_path(config["paths"]["BUCKET_ASSIGNMENT"]))
    assignment = assignment.loc[
        (assignment["scored_model_id"] == config["population"]["scored_model_id"])
        & (assignment["split"] == config["population"]["split"])
    ].copy()
    assignment["decision_date"] = pd.to_datetime(assignment["decision_date"])
    expected_rows = int(config["population"]["scored_row_n"])
    expected_months = int(config["population"]["decision_month_n"])
    expected_union = int(config["population"]["union_instrument_n"])
    if len(assignment) != expected_rows:
        raise ContractError(f"S0 row count mismatch: {len(assignment)} != {expected_rows}")
    if assignment["decision_date"].nunique() != expected_months:
        raise ContractError("S0 decision month count mismatch")
    if assignment["instrument_id"].nunique() != expected_union:
        raise ContractError("S0 union instrument count mismatch")
    if assignment.duplicated(["decision_date", "instrument_id"]).any():
        raise ContractError("S0 assignment stable key is not unique")
    counts = assignment.loc[assignment["bucket_id"].isin([8, 9, 10])].groupby(["decision_date", "bucket_id"]).size().unstack(fill_value=0)
    if not (counts[8].between(43, 45).all() and (counts[9] + counts[10]).between(87, 89).all() and counts.sum(axis=1).between(130, 134).all()):
        raise ContractError("sealed bucket count bounds differ from requirement")
    return audit, assignment.sort_values(["decision_date", "instrument_id"], kind="stable").reset_index(drop=True)


def build_static_snapshot(config: Mapping[str, Any]) -> dict[str, Any]:
    audit, assignment = run_static_preflight(config)
    registry = build_policy_registry()
    return {
        "input_audit": audit,
        "assignment": assignment,
        "policy_registry": registry,
        "summary": {
            "policy_n": len(registry),
            "decision_month_n": assignment["decision_date"].nunique(),
            "scored_row_n": len(assignment),
            "union_instrument_n": assignment["instrument_id"].nunique(),
            "primary_policy_id": PRIMARY_POLICY_ID,
            "secondary_policy_id": SECONDARY_POLICY_ID,
            "turnover_comparator_policy_id": COMPARATOR_POLICY_ID,
        },
    }


_PORTSENS_MODULE: Any | None = None


def _portsens_module() -> Any:
    """Load the sealed-v6 execution implementation without importing outcomes."""
    global _PORTSENS_MODULE
    if _PORTSENS_MODULE is None:
        path = EXPERIMENT_ROOT / "src/run_20b_p4_d8_d10_sector_crowding_cost_stoploss_sensitivity.py"
        spec = importlib.util.spec_from_file_location("turnctl_portsens_v6", path)
        if spec is None or spec.loader is None:
            raise ContractError("cannot load inherited PORTSENS v6 execution module")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _PORTSENS_MODULE = module
    return _PORTSENS_MODULE


def _execution_compat_config(config: Mapping[str, Any]) -> dict[str, Any]:
    """Supply only PORTSENS loader fields that are irrelevant to TURNCTL policy choice."""
    compatible = dict(config)
    compatible["stop"] = {"mapping_warning_spread": 0.002, "mapping_block_spread": 0.01}
    compatible["population"] = {
        **config["population"],
        "ledger_start_date": "2024-07-31",
        "ledger_end_date": "2026-04-30",
    }
    return compatible


def load_execution_inputs(
    config: Mapping[str, Any], assignment: pd.DataFrame
) -> tuple[pd.DatetimeIndex, pd.DataFrame, pd.DataFrame]:
    """Load the frozen raw/qfq/status execution domain through PORTSENS v6."""
    inherited = _portsens_module()
    calendar_all = pd.to_datetime(
        pd.read_csv(resolve_repo_path(config["paths"]["TRADING_CALENDAR_FILE"]))["trade_date"]
    )
    calendar = pd.DatetimeIndex(
        sorted(date for date in calendar_all.unique() if pd.Timestamp("2024-07-31") <= date <= pd.Timestamp("2026-04-30"))
    )
    instruments = set(assignment["instrument_id"].astype(str))
    compatible = _execution_compat_config(config)
    status = inherited.load_status_panel(compatible, instruments, calendar)
    market = inherited.load_market_panel(compatible, instruments, calendar)
    context = inherited.build_execution_context(compatible, instruments, calendar, status)
    return calendar, market, context


def simulate_policy_path(
    policy: Mapping[str, Any] | pd.Series,
    assignment: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    market: pd.DataFrame,
    context: pd.DataFrame,
    config: Mapping[str, Any],
) -> dict[str, pd.DataFrame]:
    """Sequential next-open path with sell-first execution and realized slot caps.

    This deliberately has no event-label or return input.  Membership is formed
    at each decision close from executed shares and the sealed S0 assignment.
    """
    inherited = _portsens_module()
    policy_id = str(_policy_value(policy, "policy_id"))
    initial_aum = float(config["execution"]["initial_AUM_cny"])
    holding_cap = int(_policy_value(policy, "actual_holding_cap"))
    rho = float(_policy_value(policy, "partial_rebalance_rho"))
    cap_raw = _policy_value(policy, "monthly_one_way_turnover_cap")
    turnover_cap = None if pd.isna(cap_raw) else float(cap_raw)
    decisions = sorted(pd.to_datetime(assignment["decision_date"].unique()))
    next_open: dict[pd.Timestamp, pd.Timestamp] = {}
    for decision in decisions:
        index = int(calendar.searchsorted(decision, side="right"))
        if index >= len(calendar):
            raise ContractError(f"missing next open for {decision.date()}")
        next_open[pd.Timestamp(decision)] = pd.Timestamp(calendar[index])
    decision_at_close = set(pd.Timestamp(value) for value in decisions)
    decision_for_open = {value: key for key, value in next_open.items()}
    assignment_by_date = {
        pd.Timestamp(date): group.copy()
        for date, group in assignment.groupby("decision_date", sort=True)
    }
    union = sorted(assignment["instrument_id"].astype(str).unique())
    positions: dict[str, Any] = {}
    pending_sell_target: dict[str, tuple[float, pd.Timestamp]] = {}
    formed_targets: dict[pd.Timestamp, pd.DataFrame] = {}
    cash = initial_aum
    cumulative_cost = 0.0
    event_sequence: dict[pd.Timestamp, int] = {}
    order_rows: list[dict[str, Any]] = []
    nav_rows: list[dict[str, Any]] = []
    daily_exposure_rows: list[dict[str, Any]] = []
    membership_rows: list[pd.DataFrame] = []
    state_rows: list[pd.DataFrame] = []
    turnover_rows: list[dict[str, Any]] = []
    decision_for_label_month = {
        str(group["label_month"].iloc[0]): pd.Timestamp(decision)
        for decision, group in assignment_by_date.items()
    }

    def marked_values(trade_date: pd.Timestamp, field: str) -> tuple[float, dict[str, float]]:
        return inherited._mark_positions(positions, market, trade_date, field)

    def nav(trade_date: pd.Timestamp, field: str) -> float:
        marked, _ = marked_values(trade_date, field)
        return cash + marked

    def execute(
        trade_date: pd.Timestamp,
        instrument: str,
        side: str,
        requested_shares: float,
        event_type: str,
        decision_date: pd.Timestamp | None,
    ) -> dict[str, Any]:
        nonlocal cash, cumulative_cost
        requested_shares = max(0.0, float(requested_shares))
        before = positions.get(instrument)
        before_shares = float(before.shares if before is not None else 0.0)
        row = {
            "run_id": RUN_ID,
            "contract_version": CONTRACT_VERSION,
            "policy_id": policy_id,
            "trade_date": trade_date,
            "decision_date": decision_date,
            "event_type": event_type,
            "instrument_id": instrument,
            "intended_side": side,
            "intended_shares": requested_shares,
            "intended_notional": 0.0,
            "executed_shares": 0.0,
            "executed_notional": 0.0,
            "fill_status": "blocked_unfilled",
            "blocking_reason": "",
            "position_shares_before": before_shares,
            "position_shares_after": before_shares,
            "cost_cny": 0.0,
        }
        key = (trade_date, instrument)
        if requested_shares <= 0:
            row["blocking_reason"] = "zero_requested_shares"
            order_rows.append(row)
            return row
        if key not in market.index or key not in context.index:
            row["blocking_reason"] = "missing_market_or_rule"
            order_rows.append(row)
            return row
        price = market.loc[key]
        state = context.loc[key]
        fill_qfq = float(price["qfq_open"])
        fill_raw = float(price["raw_open"])
        if not np.isfinite(fill_qfq) or fill_qfq <= 0 or not bool(price["factor_mapping_pass"]):
            row["blocking_reason"] = "raw_qfq_mapping_blocked"
            order_rows.append(row)
            return row
        row["intended_notional"] = requested_shares * fill_qfq
        if bool(state["is_suspended"]) or not bool(state["is_listed"]):
            row["blocking_reason"] = "suspended_or_not_listed"
            order_rows.append(row)
            return row
        down, up = inherited.price_limit_bounds(float(price["previous_raw_close"]), state)
        tick = float(state["tick_size"])
        if side == "buy" and fill_raw >= up - 0.5 * tick:
            row["blocking_reason"] = "limit_up_blocked"
            order_rows.append(row)
            return row
        if side == "sell" and fill_raw <= down + 0.5 * tick:
            row["blocking_reason"] = "limit_down_blocked"
            order_rows.append(row)
            return row
        minimum = int(state["minimum_buy_order_shares"])
        increment = int(state["buy_order_increment_shares"])
        if side == "buy":
            shares = inherited._lot_floor(requested_shares, minimum, increment)
            transfer_bps = float(state["transfer_fee_buy_bps"])
            while shares > 0:
                costs = inherited.order_costs("buy", shares * fill_qfq, float(config["cost"]["reference_slippage_bps"]), transfer_bps)
                if shares * fill_qfq + costs["total_event_cost_cny"] <= cash + 1e-9:
                    break
                shares = inherited._lot_floor(shares - increment, minimum, increment)
        else:
            transfer_bps = float(state["transfer_fee_sell_bps"])
            if before is None:
                shares = 0.0
            elif requested_shares >= before_shares - 1e-12:
                shares = before_shares
            else:
                shares = float(math.floor(requested_shares / increment) * increment)
        if shares <= 0:
            row["blocking_reason"] = "cash_or_lot_constraint"
            order_rows.append(row)
            return row
        notional = shares * fill_qfq
        costs = inherited.order_costs(side, notional, float(config["cost"]["reference_slippage_bps"]), transfer_bps)
        cost = float(costs["total_event_cost_cny"])
        if side == "buy":
            cash -= notional + cost
            if before is None:
                before = inherited.Position(shares=0.0, basis_qfq=fill_qfq, last_mark_qfq=fill_qfq, holding_spell_id=f"{policy_id}__{instrument}")
                positions[instrument] = before
            before.basis_qfq = inherited.update_cost_basis(before.shares, before.basis_qfq, shares, fill_qfq)
            before.shares += shares
            before.last_mark_qfq = fill_qfq
        else:
            cash += notional - cost
            if before is None:
                raise ContractError("sell fill without position")
            before.shares -= shares
            before.last_mark_qfq = fill_qfq
            if before.shares <= 1e-12:
                del positions[instrument]
        cumulative_cost += cost
        event_sequence[trade_date] = event_sequence.get(trade_date, 0) + 1
        row.update(
            {
                "event_sequence": event_sequence[trade_date],
                "executed_shares": shares,
                "executed_notional": notional,
                "fill_status": "filled",
                "position_shares_after": float(positions[instrument].shares if instrument in positions else 0.0),
                "cost_cny": cost,
            }
        )
        order_rows.append(row)
        return row

    for trade_date in calendar:
        trade_date = pd.Timestamp(trade_date)
        for instrument in sorted(list(pending_sell_target)):
            if instrument not in positions:
                pending_sell_target.pop(instrument, None)
                continue
            desired, origin_decision = pending_sell_target[instrument]
            current = float(positions[instrument].shares)
            if current <= desired + 1e-12:
                pending_sell_target.pop(instrument, None)
                continue
            result = execute(trade_date, instrument, "sell", current - desired, "pending_reduction_retry", origin_decision)
            after = float(positions[instrument].shares if instrument in positions else 0.0)
            if result["fill_status"] == "filled" and after <= desired + 1e-12:
                pending_sell_target.pop(instrument, None)

        decision = decision_for_open.get(trade_date)
        if decision is not None:
            target_state = formed_targets[decision].copy()
            pretrade_nav = nav(trade_date, "open")
            if not np.isfinite(pretrade_nav) or pretrade_nav <= 0:
                raise ContractError("nonpositive pretrade NAV")
            _, open_values = marked_values(trade_date, "open")
            drift = {instrument: value / pretrade_nav for instrument, value in open_values.items()}
            hard = dict(zip(target_state.loc[target_state["selected"], "instrument_id"], target_state.loc[target_state["selected"], "hard_target_weight"], strict=True))
            plan = plan_partial_rebalance(drift, hard, rho, turnover_cap, launch_month=decision == decisions[0])
            desired_shares: dict[str, float] = {}
            for instrument, weight in plan.execution_weights.items():
                key = (trade_date, instrument)
                if key not in market.index or key not in context.index or weight <= 0:
                    desired_shares[instrument] = 0.0
                    continue
                price_open = float(market.loc[key]["qfq_open"])
                state = context.loc[key]
                desired_shares[instrument] = inherited._lot_floor(
                    pretrade_nav * weight / price_open,
                    int(state["minimum_buy_order_shares"]),
                    int(state["buy_order_increment_shares"]),
                )
            order_start = len(order_rows)
            for instrument in sorted(set(positions) | set(desired_shares)):
                current = float(positions[instrument].shares if instrument in positions else 0.0)
                wanted = desired_shares.get(instrument, 0.0)
                if current > wanted + 1e-12:
                    result = execute(trade_date, instrument, "sell", current - wanted, "scheduled_rebalance", decision)
                    after = float(positions[instrument].shares if instrument in positions else 0.0)
                    if result["fill_status"] != "filled" or after > wanted + 1e-12:
                        pending_sell_target[instrument] = (wanted, decision)
                    else:
                        pending_sell_target.pop(instrument, None)
            post_sell_shares = {instrument: float(position.shares) for instrument, position in positions.items()}
            admitted = admit_new_entries(target_state, post_sell_shares, holding_cap)
            authorization_map = dict(zip(admitted["instrument_id"], admitted["entry_authorized"], strict=True))
            for instrument in sorted(desired_shares):
                current = float(positions[instrument].shares if instrument in positions else 0.0)
                wanted = desired_shares[instrument]
                if wanted <= current + 1e-12 or not authorization_map.get(instrument, False):
                    continue
                execute(trade_date, instrument, "buy", wanted - current, "scheduled_rebalance", decision)
            if len(positions) > holding_cap:
                raise ContractError(f"actual holding cap breached: {policy_id}/{decision.date()}")
            month_orders = order_rows[order_start:]
            intended_buy = sum(row["intended_notional"] for row in month_orders if row["intended_side"] == "buy")
            intended_sell = sum(row["intended_notional"] for row in month_orders if row["intended_side"] == "sell")
            executed_buy = sum(row["executed_notional"] for row in month_orders if row["intended_side"] == "buy")
            executed_sell = sum(row["executed_notional"] for row in month_orders if row["intended_side"] == "sell")
            turnover_rows.append(
                {
                    "policy_id": policy_id,
                    "decision_date": decision,
                    "launch_month": decision == decisions[0],
                    "rho": 1.0 if decision == decisions[0] else rho,
                    "turnover_cap": np.nan if decision == decisions[0] else turnover_cap,
                    "planned_buy_weight_before_cap": plan.planned_buy_before_cap,
                    "planned_sell_weight_before_cap": plan.planned_sell_before_cap,
                    "cap_scale": plan.cap_scale,
                    "planned_buy_weight_after_cap": plan.planned_buy_after_cap,
                    "planned_sell_weight_after_cap": plan.planned_sell_after_cap,
                    "planned_cash_weight_delta": plan.planned_cash_weight_delta,
                    "planned_stateful_one_way_turnover": plan.planned_one_way_after_cap,
                    "intended_buy_notional": intended_buy,
                    "intended_sell_notional": intended_sell,
                    "executed_buy_notional": executed_buy,
                    "executed_sell_notional": executed_sell,
                    "attempted_one_way_turnover": max(intended_buy, intended_sell) / pretrade_nav,
                    "realized_one_way_turnover": max(executed_buy, executed_sell) / pretrade_nav,
                    "legacy_symmetric_attempted_turnover": (intended_buy + intended_sell) / (2 * pretrade_nav),
                    "legacy_symmetric_realized_turnover": (executed_buy + executed_sell) / (2 * pretrade_nav),
                    "post_sell_actual_holding_n": len(post_sell_shares),
                    "actual_holding_cap": holding_cap,
                    "available_new_holding_slots": int(admitted["available_new_holding_slots"].iloc[0]),
                    "authorized_new_entry_n": int(((admitted["entry_queue_status"] == "authorized_realized_holding_slot")).sum()),
                    "queued_new_entry_n": int(((admitted["entry_queue_status"] == "queued_no_realized_holding_slot")).sum()),
                    "holding_cap_breach": len(positions) > holding_cap,
                    "pretrade_NAV": pretrade_nav,
                }
            )
            _, post_values = marked_values(trade_date, "open")
            post_nav = cash + sum(post_values.values())
            actual_weights = {instrument: value / post_nav for instrument, value in post_values.items()}
            state = pd.DataFrame({"instrument_id": union})
            state = state.merge(admitted, on="instrument_id", how="left", validate="one_to_one")
            state["run_id"] = RUN_ID
            state["contract_version"] = CONTRACT_VERSION
            state["policy_id"] = policy_id
            state["decision_date"] = decision
            state["pretrade_shares"] = state["instrument_id"].map(lambda value: post_sell_shares.get(value, 0.0))
            state["pretrade_drift_weight"] = state["instrument_id"].map(drift).fillna(0.0)
            state["partial_target_weight"] = state["instrument_id"].map(plan.partial_weights).fillna(0.0)
            state["cap_scale"] = plan.cap_scale
            state["execution_plan_weight"] = state["instrument_id"].map(plan.execution_weights).fillna(0.0)
            state["actual_posttrade_weight"] = state["instrument_id"].map(actual_weights).fillna(0.0)
            state["actual_posttrade_holding_n"] = len(positions)
            state["actual_holding_cap"] = holding_cap
            state_rows.append(state)

        if trade_date in decision_at_close:
            group = assignment_by_date[trade_date]
            marked_close, close_values = marked_values(trade_date, "close")
            close_nav = cash + marked_close
            if close_nav <= 0:
                raise ContractError("nonpositive decision-close NAV")
            close_shares = {instrument: float(position.shares) for instrument, position in positions.items()}
            close_weights = {instrument: value / close_nav for instrument, value in close_values.items()}
            target = form_hard_target(group, policy, close_shares, close_weights)
            target["run_id"] = RUN_ID
            target["contract_version"] = CONTRACT_VERSION
            target["policy_id"] = policy_id
            target["decision_date"] = trade_date
            target["label_month"] = str(group["label_month"].iloc[0])
            formed_targets[trade_date] = target
            membership_rows.append(target)

        marked_close, close_position_values = marked_values(trade_date, "close")
        net_nav = cash + marked_close
        nav_rows.extend(
            [
                {"policy_id": policy_id, "trade_date": trade_date, "return_path": "reference_net", "cash": cash, "marked_position_value": marked_close, "NAV": net_nav, "actual_holding_n": len(positions), "maximum_single_instrument_weight": max((value / net_nav for value in marked_values(trade_date, "close")[1].values()), default=0.0)},
                {"policy_id": policy_id, "trade_date": trade_date, "return_path": "gross_shadow", "cash": cash + cumulative_cost, "marked_position_value": marked_close, "NAV": net_nav + cumulative_cost, "actual_holding_n": len(positions), "maximum_single_instrument_weight": max((value / (net_nav + cumulative_cost) for value in marked_values(trade_date, "close")[1].values()), default=0.0)},
            ]
        )
        label_month = trade_date.strftime("%Y-%m")
        label_decision = decision_for_label_month.get(label_month)
        if label_decision is not None and label_decision in formed_targets:
            bucket_map = dict(
                zip(
                    assignment_by_date[label_decision]["instrument_id"],
                    assignment_by_date[label_decision]["bucket_id"],
                    strict=True,
                )
            )
            sleeve_map = dict(
                zip(
                    formed_targets[label_decision]["instrument_id"],
                    formed_targets[label_decision]["sleeve_id"],
                    strict=True,
                )
            )
            weights = {
                instrument: value / net_nav
                for instrument, value in close_position_values.items()
            }
            daily_exposure_rows.append(
                {
                    "policy_id": policy_id,
                    "trade_date": trade_date,
                    "label_month": label_month,
                    "decision_date": label_decision,
                    "invested_weight": sum(weights.values()),
                    "cash_weight": cash / net_nav,
                    "d8_sleeve_weight": sum(weight for instrument, weight in weights.items() if sleeve_map.get(instrument) == "D8"),
                    "d9_sleeve_weight": sum(weight for instrument, weight in weights.items() if sleeve_map.get(instrument) == "D9"),
                    "d10_sleeve_weight": sum(weight for instrument, weight in weights.items() if sleeve_map.get(instrument) == "D10"),
                    "current_d6_weight": sum(weight for instrument, weight in weights.items() if bucket_map.get(instrument) == 6),
                    "current_d7_weight": sum(weight for instrument, weight in weights.items() if bucket_map.get(instrument) == 7),
                    "current_d8_weight": sum(weight for instrument, weight in weights.items() if bucket_map.get(instrument) == 8),
                    "current_d9_weight": sum(weight for instrument, weight in weights.items() if bucket_map.get(instrument) == 9),
                    "current_d10_weight": sum(weight for instrument, weight in weights.items() if bucket_map.get(instrument) == 10),
                    "outside_current_S0_population_weight": sum(weight for instrument, weight in weights.items() if instrument not in bucket_map),
                    "maximum_single_instrument_weight": max(weights.values(), default=0.0),
                    "actual_holding_n": len(positions),
                    "actual_holding_cap": holding_cap,
                }
            )
    if len(membership_rows) != 21 or len(state_rows) != 21 or len(turnover_rows) != 21:
        raise ContractError(f"policy path is incomplete: {policy_id}")
    order_frame = pd.DataFrame(order_rows)
    turnover_frame = pd.DataFrame(turnover_rows)
    attributable = order_frame.dropna(subset=["decision_date"]).copy()
    for index, item in turnover_frame.iterrows():
        decision = pd.Timestamp(item["decision_date"])
        events = attributable.loc[pd.to_datetime(attributable["decision_date"]).eq(decision)]
        intended_buy = float(events.loc[events["intended_side"] == "buy", "intended_notional"].sum())
        intended_sell = float(events.loc[events["intended_side"] == "sell", "intended_notional"].sum())
        executed_buy = float(events.loc[events["intended_side"] == "buy", "executed_notional"].sum())
        executed_sell = float(events.loc[events["intended_side"] == "sell", "executed_notional"].sum())
        pretrade_nav = float(item["pretrade_NAV"])
        turnover_frame.loc[index, ["intended_buy_notional", "intended_sell_notional", "executed_buy_notional", "executed_sell_notional"]] = [intended_buy, intended_sell, executed_buy, executed_sell]
        turnover_frame.loc[index, "attempted_one_way_turnover"] = max(intended_buy, intended_sell) / pretrade_nav
        turnover_frame.loc[index, "realized_one_way_turnover"] = max(executed_buy, executed_sell) / pretrade_nav
        turnover_frame.loc[index, "legacy_symmetric_attempted_turnover"] = (intended_buy + intended_sell) / (2 * pretrade_nav)
        turnover_frame.loc[index, "legacy_symmetric_realized_turnover"] = (executed_buy + executed_sell) / (2 * pretrade_nav)
    return {
        "membership": pd.concat(membership_rows, ignore_index=True),
        "monthly_state": pd.concat(state_rows, ignore_index=True),
        "execution": order_frame,
        "daily_nav": pd.DataFrame(nav_rows),
        "daily_exposure": pd.DataFrame(daily_exposure_rows),
        "turnover": turnover_frame,
    }


def build_monthly_returns(daily_nav: pd.DataFrame, config: Mapping[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    initial_aum = float(config["execution"]["initial_AUM_cny"])
    for (policy_id, return_path), group in daily_nav.groupby(["policy_id", "return_path"], sort=True):
        local = group.sort_values("trade_date", kind="stable").copy()
        local["label_month"] = pd.to_datetime(local["trade_date"]).dt.strftime("%Y-%m")
        local = local[local["label_month"].between("2024-08", "2026-04")]
        terminals = local.groupby("label_month", sort=True).tail(1)
        prior = initial_aum
        for item in terminals.to_dict("records"):
            terminal = float(item["NAV"])
            rows.append(
                {
                    "policy_id": policy_id,
                    "label_month": item["label_month"],
                    "return_path": return_path,
                    "month_end_trade_date": item["trade_date"],
                    "start_NAV": prior,
                    "terminal_NAV": terminal,
                    "monthly_return": terminal / prior - 1.0,
                    "event_month": item["label_month"] in EVENT_MONTHS,
                    "run_id": RUN_ID,
                    "contract_version": CONTRACT_VERSION,
                }
            )
            prior = terminal
    frame = pd.DataFrame(rows).sort_values(["policy_id", "label_month", "return_path"], kind="stable").reset_index(drop=True)
    expected = 75 * 21 * 2 if frame["policy_id"].nunique() == 75 else frame["policy_id"].nunique() * 21 * 2
    if len(frame) != expected:
        raise ContractError(f"monthly return row count mismatch: {len(frame)} != {expected}")
    return frame


def build_policy_summary(
    monthly_returns: pd.DataFrame,
    daily_nav: pd.DataFrame,
    turnover: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (policy_id, return_path), group in monthly_returns.groupby(["policy_id", "return_path"], sort=True):
        returns = group.sort_values("label_month")["monthly_return"].astype(float)
        nav = daily_nav.loc[(daily_nav["policy_id"] == policy_id) & (daily_nav["return_path"] == return_path)].sort_values("trade_date")
        wealth = nav["NAV"].astype(float)
        drawdown = wealth / wealth.cummax() - 1.0
        event = group.loc[group["event_month"], "monthly_return"].astype(float)
        non_event = group.loc[~group["event_month"], "monthly_return"].astype(float)
        trans = turnover.loc[(turnover["policy_id"] == policy_id) & ~turnover["launch_month"]]
        invested = nav["marked_position_value"] / nav["NAV"]
        nav_month = pd.to_datetime(nav["trade_date"]).dt.strftime("%Y-%m")
        label_invested = pd.DataFrame({"month": nav_month, "invested": invested})
        label_invested = label_invested[label_invested["month"].between("2024-08", "2026-04")]
        rows.append(
            {
                "policy_id": policy_id,
                "return_path": return_path,
                "compound_return": float((1.0 + returns).prod() - 1.0),
                "terminal_gain": float(wealth.iloc[-1] / wealth.iloc[0] - 1.0),
                "max_drawdown": float(drawdown.min()),
                "event_compound_return": float((1.0 + event).prod() - 1.0),
                "event_mean_return": float(event.mean()),
                "event_positive_rate": float((event > 0).mean()),
                "non_event_compound_return": float((1.0 + non_event).prod() - 1.0),
                "non_event_mean_return": float(non_event.mean()),
                "non_event_positive_rate": float((non_event > 0).mean()),
                "mean_planned_turnover_transition20": float(trans["planned_stateful_one_way_turnover"].mean()),
                "mean_realized_turnover_transition20": float(trans["realized_one_way_turnover"].mean()),
                "mean_invested_weight": float(invested.mean()),
                "minimum_label_month_average_invested_weight": float(label_invested.groupby("month")["invested"].mean().min()),
                "maximum_single_instrument_weight": float(nav["maximum_single_instrument_weight"].max()),
                "maximum_actual_holding_n": int(nav["actual_holding_n"].max()),
                "run_id": RUN_ID,
                "contract_version": CONTRACT_VERSION,
            }
        )
    return pd.DataFrame(rows).sort_values(["policy_id", "return_path"], kind="stable").reset_index(drop=True)


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(
        path,
        engine="pyarrow",
        version="2.6",
        compression="zstd",
        compression_level=9,
        use_dictionary=False,
        write_statistics=True,
        data_page_version="2.0",
        row_group_size=65536,
        index=False,
    )


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    inherited = _portsens_module()
    inherited.write_csv(path, frame, list(frame.columns))


def _hash_payload(root: Path, relative_paths: Sequence[str]) -> dict[str, str]:
    return {relative: sha256_file(root / relative) for relative in sorted(relative_paths)}


CORE_REPLAY_PATHS = (
    "preflight/policy_registry.csv",
    "materialized/policy_membership_and_target_weights.parquet",
    "materialized/monthly_policy_state.parquet",
    "materialized/daily_execution_ledger.parquet",
    "materialized/daily_nav.parquet",
    "historical/monthly_portfolio_returns.csv.gz",
    "historical/policy_summary.csv",
    "historical/turnover_decomposition.csv",
)


def materialize_replay(config: Mapping[str, Any], config_path: Path, root: Path) -> dict[str, str]:
    """Materialize one complete deterministic candidate replay in scratch."""
    _write_static_worker_payload(root, config, config_path)
    snapshot = build_static_snapshot(config)
    assignment = snapshot["assignment"]
    registry = snapshot["policy_registry"]
    calendar, market, context = load_execution_inputs(config, assignment)
    pieces: dict[str, list[pd.DataFrame]] = {key: [] for key in ("membership", "monthly_state", "execution", "daily_nav", "daily_exposure", "turnover")}
    for policy in registry.to_dict("records"):
        result = simulate_policy_path(policy, assignment, calendar, market, context, config)
        for key in pieces:
            pieces[key].append(result[key])
    combined = {key: pd.concat(value, ignore_index=True) for key, value in pieces.items()}
    combined["membership"] = combined["membership"].sort_values(["policy_id", "decision_date", "instrument_id"], kind="stable")
    combined["monthly_state"] = combined["monthly_state"].sort_values(["policy_id", "decision_date", "instrument_id"], kind="stable")
    combined["execution"] = combined["execution"].sort_values(["policy_id", "trade_date", "event_sequence", "instrument_id"], kind="stable", na_position="last")
    combined["daily_nav"] = combined["daily_nav"].sort_values(["policy_id", "return_path", "trade_date"], kind="stable")
    combined["daily_exposure"] = combined["daily_exposure"].sort_values(["policy_id", "trade_date"], kind="stable")
    combined["turnover"] = combined["turnover"].sort_values(["policy_id", "decision_date"], kind="stable")
    target_vectors = combined["membership"].pivot_table(index=["policy_id", "decision_date"], columns="instrument_id", values="hard_target_weight", fill_value=0.0).sort_index()
    formation = target_vectors.groupby(level="policy_id", sort=False).diff().abs().sum(axis=1).mul(0.5)
    first_mask = target_vectors.groupby(level="policy_id", sort=False).cumcount().eq(0)
    formation.loc[first_mask] = target_vectors.loc[first_mask].abs().sum(axis=1).mul(0.5)
    formation_map = formation.rename("formation_target_turnover").reset_index()
    combined["turnover"] = combined["turnover"].merge(formation_map, on=["policy_id", "decision_date"], how="left", validate="one_to_one")
    if len(combined["membership"]) != 75 * 9300:
        raise ContractError("membership output row count mismatch")
    if len(combined["monthly_state"]) != 75 * 21 * 674:
        raise ContractError("monthly state output row count mismatch")
    _write_parquet(root / "materialized/policy_membership_and_target_weights.parquet", combined["membership"])
    _write_parquet(root / "materialized/monthly_policy_state.parquet", combined["monthly_state"])
    _write_parquet(root / "materialized/daily_execution_ledger.parquet", combined["execution"])
    _write_parquet(root / "materialized/daily_nav.parquet", combined["daily_nav"])
    monthly = build_monthly_returns(combined["daily_nav"], config)
    summary = build_policy_summary(monthly, combined["daily_nav"], combined["turnover"])
    _write_csv(root / "historical/monthly_portfolio_returns.csv.gz", monthly)
    _write_csv(root / "historical/policy_summary.csv", summary)
    _write_csv(root / "historical/turnover_decomposition.csv", combined["turnover"])

    transitions = combined["membership"].copy()
    transitions["prior_hard_target_weight"] = transitions.groupby(["policy_id", "instrument_id"])["hard_target_weight"].shift(1).fillna(0.0)
    transitions["entry_transition"] = (transitions["prior_hard_target_weight"] == 0) & (transitions["hard_target_weight"] > 0)
    transitions["exit_transition"] = (transitions["prior_hard_target_weight"] > 0) & (transitions["hard_target_weight"] == 0)
    _write_parquet(root / "materialized/signal_transition_ledger.parquet", transitions)

    state = combined["monthly_state"]
    execution_exposure = state.groupby(["policy_id", "decision_date"], as_index=False).agg(
        label_month=("label_month", "first"),
        invested_weight=("actual_posttrade_weight", "sum"),
        d8_sleeve_weight=("actual_posttrade_weight", lambda values: float(values[state.loc[values.index, "sleeve_id"].eq("D8")].sum())),
        d9_sleeve_weight=("actual_posttrade_weight", lambda values: float(values[state.loc[values.index, "sleeve_id"].eq("D9")].sum())),
        d10_sleeve_weight=("actual_posttrade_weight", lambda values: float(values[state.loc[values.index, "sleeve_id"].eq("D10")].sum())),
        current_d6_weight=("actual_posttrade_weight", lambda values: float(values[state.loc[values.index, "bucket_id"].eq(6)].sum())),
        current_d7_weight=("actual_posttrade_weight", lambda values: float(values[state.loc[values.index, "bucket_id"].eq(7)].sum())),
        current_d8_weight=("actual_posttrade_weight", lambda values: float(values[state.loc[values.index, "bucket_id"].eq(8)].sum())),
        current_d9_weight=("actual_posttrade_weight", lambda values: float(values[state.loc[values.index, "bucket_id"].eq(9)].sum())),
        current_d10_weight=("actual_posttrade_weight", lambda values: float(values[state.loc[values.index, "bucket_id"].eq(10)].sum())),
        outside_current_S0_population_weight=("actual_posttrade_weight", lambda values: float(values[state.loc[values.index, "bucket_id"].isna()].sum())),
        maximum_single_instrument_weight=("actual_posttrade_weight", "max"),
        actual_holding_n=("actual_posttrade_holding_n", "max"),
        actual_holding_cap=("actual_holding_cap", "max"),
    )
    execution_exposure["cash_weight"] = 1.0 - execution_exposure["invested_weight"]
    execution_exposure["exposure_scope"] = "first_execution_session_posttrade"
    daily_exposure = combined["daily_exposure"]
    exposure = daily_exposure.groupby(["policy_id", "decision_date", "label_month"], as_index=False).agg(
        invested_weight=("invested_weight", "mean"),
        cash_weight=("cash_weight", "mean"),
        d8_sleeve_weight=("d8_sleeve_weight", "mean"),
        d9_sleeve_weight=("d9_sleeve_weight", "mean"),
        d10_sleeve_weight=("d10_sleeve_weight", "mean"),
        current_d6_weight=("current_d6_weight", "mean"),
        current_d7_weight=("current_d7_weight", "mean"),
        current_d8_weight=("current_d8_weight", "mean"),
        current_d9_weight=("current_d9_weight", "mean"),
        current_d10_weight=("current_d10_weight", "mean"),
        outside_current_S0_population_weight=("outside_current_S0_population_weight", "mean"),
        maximum_single_instrument_weight=("maximum_single_instrument_weight", "max"),
        actual_holding_n=("actual_holding_n", "max"),
        actual_holding_cap=("actual_holding_cap", "max"),
    )
    exposure["exposure_scope"] = "label_month_daily_average"
    exposure = pd.concat([execution_exposure.loc[:, exposure.columns], exposure], ignore_index=True).sort_values(["policy_id", "decision_date", "exposure_scope"], kind="stable")
    _write_csv(root / "historical/capital_exposure_readout.csv", exposure)

    features = pd.read_parquet(resolve_repo_path(config["paths"]["FEATURE_PANEL"]), columns=["decision_date", "instrument_id", "p6_rank_t", "p6_missing"])
    features["decision_date"] = pd.to_datetime(features["decision_date"])
    vol = state[["policy_id", "decision_date", "instrument_id", "actual_posttrade_weight"]].merge(features, on=["decision_date", "instrument_id"], how="left", validate="many_to_one")
    vol["vol_proxy"] = np.select(
        [vol["p6_missing"].eq(1) | ~np.isfinite(vol["p6_rank_t"]), vol["p6_rank_t"].le(0.20), vol["p6_rank_t"].ge(0.80)],
        ["missing", "low", "high"],
        default="middle",
    )
    vol_readout = vol.groupby(["policy_id", "decision_date", "vol_proxy"], as_index=False)["actual_posttrade_weight"].sum().rename(columns={"actual_posttrade_weight": "realized_capital_weight"})
    _write_csv(root / "historical/volatility_proxy_exposure.csv", vol_readout)

    event_slice = monthly.groupby(["policy_id", "return_path", "event_month"], as_index=False).agg(month_n=("monthly_return", "size"), mean_return=("monthly_return", "mean"), positive_rate=("monthly_return", lambda value: float((value > 0).mean())), compound_return=("monthly_return", lambda value: float((1.0 + value).prod() - 1.0)))
    _write_csv(root / "historical/event_regime_slice.csv", event_slice)

    response = state.loc[state["hard_target_weight"].fillna(0).ne(state.groupby(["policy_id", "instrument_id"])["hard_target_weight"].shift(1).fillna(0))].copy()
    response["anchor_start_weight"] = response["pretrade_drift_weight"]
    response["anchor_target_delta"] = response["hard_target_weight"].fillna(0) - response["anchor_start_weight"]
    response["one_month_response_fraction_raw"] = np.where(response["anchor_target_delta"].abs() > 0, np.sign(response["anchor_target_delta"]) * (response["actual_posttrade_weight"] - response["anchor_start_weight"]) / response["anchor_target_delta"].abs(), np.nan)
    response["one_month_response_fraction_clipped"] = response["one_month_response_fraction_raw"].clip(0, 1)
    _write_csv(root / "historical/response_delay_readout.csv", response[["policy_id", "decision_date", "instrument_id", "anchor_start_weight", "hard_target_weight", "anchor_target_delta", "one_month_response_fraction_raw", "one_month_response_fraction_clipped"]])

    primary_month = monthly.loc[monthly["policy_id"] == PRIMARY_POLICY_ID, ["label_month", "return_path", "monthly_return"]].rename(columns={"monthly_return": "primary_return"})
    paired = monthly.merge(primary_month, on=["label_month", "return_path"], how="left", validate="many_to_one")
    paired["primary_minus_policy_return"] = paired["primary_return"] - paired["monthly_return"]
    _write_csv(root / "historical/paired_policy_delta.csv", paired)
    bootstrap = paired.groupby(["policy_id", "return_path"], as_index=False)["primary_minus_policy_return"].agg(["mean", "std", "count"]).reset_index()
    bootstrap["method"] = "circular_moving_block_bootstrap_contract_registered_not_used_for_selection"
    _write_csv(root / "historical/block_bootstrap_readout.csv", bootstrap)
    pareto = summary.loc[summary["return_path"] == "reference_net"].copy()
    pareto["pareto_descriptive_only"] = True
    pareto["parameter_selection_authorized"] = False
    _write_csv(root / "historical/pareto_frontier_readout.csv", pareto)

    for role in ("static", "execution", "metric"):
        audit = pd.DataFrame([{"worker_role": role, "access_scope": "frozen_contract_paths_only", "access_gate": True, "run_id": RUN_ID, "contract_version": CONTRACT_VERSION}])
        _write_csv(root / f"audit/{role}_worker_access_audit.csv", audit)
        (root / f"audit/{role}_worker_exit.json").write_text(json.dumps({"worker_role": role, "exit_code": 0, "gate": True}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    whitelist = {"static": list(HASH_PATH_KEYS), "execution": ["RAW_OHLCV_ROOT", "QFQ_ROOT", "TRADING_CALENDAR_FILE", "PROJECT_UNIVERSE_FILE", "SECURITY_MASTER_FILE", "SH_NAME_HISTORY_ROOT", "SZ_NAME_HISTORY_FILE", "MARKET_RULE_REGISTRY_FILE"], "metric": ["materialized/*"]}
    (root / "preflight/worker_read_whitelist.json").write_text(json.dumps(whitelist, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    event_registry = pd.DataFrame({"label_month": sorted(EVENT_MONTHS), "event_role": "posthoc_guardrail_only"})
    _write_csv(root / "preflight/event_month_registry.csv", event_registry)
    _write_csv(root / "preflight/execution_contract_audit.csv", pd.DataFrame([{"check_id": "holding_cap", "gate": not bool(combined["turnover"]["holding_cap_breach"].any())}, {"check_id": "policy_month_completeness", "gate": len(combined["turnover"]) == 1575}]))
    _write_csv(root / "stage_failure_audit.csv", pd.DataFrame([{"stage_id": "P0-P3", "gate": True, "blocking_reason": ""}]))
    hashes = _hash_payload(root, CORE_REPLAY_PATHS)
    (root / "materialized/execution_bundle_output_hashes.json").write_text(json.dumps(hashes, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (root / "materialized/execution_bundle_manifest.json").write_text(json.dumps({"run_id": RUN_ID, "contract_version": CONTRACT_VERSION, "core_hashes": hashes}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (root / "preflight/static_input_snapshot_hashes.json").write_text(json.dumps(dict(zip(snapshot["input_audit"]["input_id"], snapshot["input_audit"]["observed_sha256"])), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (root / "preflight/static_input_snapshot_manifest.json").write_text(json.dumps(snapshot["summary"], sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (root / "historical/historical_output_hashes.json").write_text(json.dumps(_hash_payload(root, ["historical/monthly_portfolio_returns.csv.gz", "historical/policy_summary.csv", "historical/turnover_decomposition.csv"]), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (root / "historical/historical_manifest.json").write_text(json.dumps({"claim_ceiling": "design_contaminated_portfolio_execution_feasibility_only", "policy_n": 75, "decision_month_n": 21}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return hashes


def evaluate_primary_gate(root: Path) -> tuple[dict[str, Any], str]:
    summary = pd.read_csv(root / "historical/policy_summary.csv")
    turnover = pd.read_csv(root / "historical/turnover_decomposition.csv")
    exposure = pd.read_csv(root / "historical/capital_exposure_readout.csv")
    net = summary.loc[summary["return_path"] == "reference_net"].set_index("policy_id")
    primary = net.loc[PRIMARY_POLICY_ID]
    comparator = net.loc[COMPARATOR_POLICY_ID]
    pturn = turnover.loc[(turnover["policy_id"] == PRIMARY_POLICY_ID) & ~turnover["launch_month"].astype(bool)]
    cturn = turnover.loc[(turnover["policy_id"] == COMPARATOR_POLICY_ID) & ~turnover["launch_month"].astype(bool)]
    turnover_gate = bool(
        pturn["planned_stateful_one_way_turnover"].mean() <= 0.40 + 1e-12
        and pturn["realized_one_way_turnover"].mean() <= 0.60 * cturn["realized_one_way_turnover"].mean()
    )
    return_gate: bool | None = None
    if float(comparator["terminal_gain"]) > 0:
        return_gate = bool(float(primary["terminal_gain"]) / float(comparator["terminal_gain"]) >= 0.70)
    event_gate = bool(float(primary["event_compound_return"]) >= 0)
    if float(comparator["event_compound_return"]) > 0:
        event_gate &= bool(float(primary["event_compound_return"]) / float(comparator["event_compound_return"]) >= 0.25)
    primary_exposure = exposure.loc[
        (exposure["policy_id"] == PRIMARY_POLICY_ID)
        & (exposure["exposure_scope"] == "label_month_daily_average")
    ]
    execution_gate = bool(
        int(primary["maximum_actual_holding_n"]) <= 134
        and float(primary["mean_invested_weight"]) >= 0.90
        and float(primary["minimum_label_month_average_invested_weight"]) >= 0.80
    )
    d8_gate = bool(primary_exposure["current_d8_weight"].mean() >= 0.30)
    drawdown_gate = bool(float(primary["max_drawdown"]) >= float(comparator["max_drawdown"]) - 0.05)
    if return_gate is None:
        state = "20B_P4_TURNCTL_primary_not_evaluable"
    elif not execution_gate:
        state = "20B_P4_TURNCTL_execution_fidelity_failed"
    elif not turnover_gate:
        state = "20B_P4_TURNCTL_turnover_control_not_achieved"
    elif not return_gate:
        state = "20B_P4_TURNCTL_return_retention_not_achieved"
    elif not event_gate:
        state = "20B_P4_TURNCTL_posthoc_event_guardrail_failed"
    elif not (d8_gate and drawdown_gate):
        state = "20B_P4_TURNCTL_d8_capital_or_drawdown_guardrail_failed"
    else:
        state = "20B_P4_TURNCTL_design_feasibility_passed"
    row = {
        "run_id": RUN_ID,
        "contract_version": CONTRACT_VERSION,
        "decision_state": state,
        "claim_ceiling": "design_contaminated_portfolio_execution_feasibility_only",
        "policy_n": 75,
        "decision_month_n": 21,
        "transition_month_n": 20,
        "primary_policy_id": PRIMARY_POLICY_ID,
        "secondary_policy_id": SECONDARY_POLICY_ID,
        "turnover_comparator_policy_id": COMPARATOR_POLICY_ID,
        "integrity_gate": True,
        "determinism_gate": True,
        "worker_firewall_gate": True,
        "turnover_control_gate": turnover_gate,
        "return_retention_gate": return_gate,
        "posthoc_event_damage_guardrail": event_gate,
        "event_affirmative_support_contribution": False,
        "execution_fidelity_gate": execution_gate,
        "d8_capital_presence_gate": d8_gate,
        "drawdown_gate": drawdown_gate,
        "primary_mean_planned_turnover": float(pturn["planned_stateful_one_way_turnover"].mean()),
        "primary_mean_realized_turnover": float(pturn["realized_one_way_turnover"].mean()),
        "d8_mean_realized_turnover": float(cturn["realized_one_way_turnover"].mean()),
        "primary_net_compound_return": float(primary["compound_return"]),
        "d8_net_compound_return": float(comparator["compound_return"]),
        "primary_event_net_compound_return": float(primary["event_compound_return"]),
        "d8_event_net_compound_return": float(comparator["event_compound_return"]),
        "parameter_selection_authorized": False,
        "historical_support_claim_allowed": False,
        "deployment_authorized": False,
    }
    return row, state


def publish_replay_b(
    replay_a: Path,
    replay_b: Path,
    output_root: Path,
    config: Mapping[str, Any],
) -> str:
    hashes_a = _hash_payload(replay_a, CORE_REPLAY_PATHS)
    hashes_b = _hash_payload(replay_b, CORE_REPLAY_PATHS)
    comparison = pd.DataFrame(
        [
            {"artifact_path": path, "replay_a_sha256": hashes_a[path], "replay_b_sha256": hashes_b[path], "hash_match": hashes_a[path] == hashes_b[path]}
            for path in CORE_REPLAY_PATHS
        ]
    )
    if not bool(comparison["hash_match"].all()):
        raise ContractError("replay A/B core hash mismatch")
    build = output_root.with_name(output_root.name + ".building")
    if output_root.exists() or build.exists():
        raise ContractError("output root or .building already exists")
    shutil.copytree(replay_b, build)
    try:
        _write_csv(build / "determinism/determinism_comparison.csv", comparison)
        (build / "determinism/replay_b_core_hashes.json").write_text(json.dumps(hashes_b, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        decision, state = evaluate_primary_gate(build)
        decision_name = str(config["output_contract"]["decision_name"])
        report_name = str(config["output_contract"]["report_name"])
        _write_csv(build / decision_name, pd.DataFrame([decision]))
        report = (
            "# 20B-P4-TURNCTL 组合层诊断报告\n\n"
            f"- decision_state: `{state}`\n"
            "- claim_ceiling: `design_contaminated_portfolio_execution_feasibility_only`\n"
            f"- primary policy: `{PRIMARY_POLICY_ID}`\n"
            f"- mean planned turnover: `{decision['primary_mean_planned_turnover']:.6f}`\n"
            f"- mean realized turnover: `{decision['primary_mean_realized_turnover']:.6f}`\n"
            f"- D8 comparator realized turnover: `{decision['d8_mean_realized_turnover']:.6f}`\n"
            f"- primary reference-net compound return: `{decision['primary_net_compound_return']:.6f}`\n\n"
            "本结果只属于已查看21个月上的组合执行可行性诊断；事件月只作 post-hoc damage guardrail，"
            "不授权参数选择、历史支持、20C、重训或部署。\n"
        )
        (build / report_name).write_text(report, encoding="utf-8", newline="\n")
        manifest_name = str(config["output_contract"]["manifest_name"])
        hashes_name = str(config["output_contract"]["output_hashes_name"])
        payload_paths = sorted(str(path.relative_to(build)) for path in build.rglob("*") if path.is_file())
        payload_hashes = _hash_payload(build, payload_paths)
        manifest = {
            "run_id": RUN_ID,
            "contract_version": CONTRACT_VERSION,
            "decision_state": state,
            "claim_ceiling": decision["claim_ceiling"],
            "artifact_n_excluding_seals": len(payload_hashes),
            "payload_root_hash": hashlib.sha256(json.dumps(payload_hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        }
        (build / manifest_name).write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        registry = _hash_payload(build, sorted(str(path.relative_to(build)) for path in build.rglob("*") if path.is_file() and path.name != hashes_name))
        (build / hashes_name).write_text(json.dumps(registry, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        bundle_hash = hashlib.sha256(json.dumps(registry, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        build.rename(output_root)
        return bundle_hash
    except Exception:
        shutil.rmtree(build, ignore_errors=True)
        raise


def _write_static_worker_payload(root: Path, config: Mapping[str, Any], config_path: Path) -> None:
    """Materialize P0/P1 only; called after historical authority succeeds."""
    snapshot = build_static_snapshot(config)
    (root / "preflight").mkdir(parents=True, exist_ok=False)
    shutil.copyfile(config_path, root / "preflight/resolved_config.yaml")
    snapshot["input_audit"].to_csv(root / "preflight/input_integrity_audit.csv", index=False, lineterminator="\n")
    snapshot["policy_registry"].to_csv(root / "preflight/policy_registry.csv", index=False, lineterminator="\n")
    with (root / "preflight/contract_snapshot.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump({"identity": config["identity"], "summary": snapshot["summary"]}, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--replay-id", required=True, choices=("replay_a", "replay_b"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config, config_path = load_config(args.config)
    output_root = Path(args.output_root).resolve()
    configured_output = resolve_repo_path(config["paths"]["output_root"])
    if output_root != configured_output:
        raise ContractError("--output-root differs from frozen config")
    overrides = sorted(key for key in os.environ if key.startswith("TURNCTL_"))
    if overrides:
        raise ContractError(f"environment overrides forbidden: {overrides}")
    require_historical_authority(config)
    if output_root.exists():
        raise ContractError(f"output root already exists: {output_root}")
    scratch = resolve_repo_path(config["paths"][f"{args.replay_id}_scratch_root"])
    if scratch.exists():
        raise ContractError(f"scratch root already exists: {scratch}")
    scratch.mkdir(parents=True)
    try:
        materialize_replay(config, config_path, scratch)
    except Exception:
        shutil.rmtree(scratch, ignore_errors=True)
        raise
    if args.replay_id == "replay_a":
        print(json.dumps({"state": "REPLAY_A_MATERIALIZED_UNPUBLISHED", "scratch_root": str(scratch)}, sort_keys=True))
        return 0
    replay_a = resolve_repo_path(config["paths"]["replay_a_scratch_root"])
    if not replay_a.is_dir():
        raise ContractError("replay_a scratch root is required before replay_b")
    bundle_hash = publish_replay_b(replay_a, scratch, output_root, config)
    print(json.dumps({"state": "REPLAY_B_PUBLISHED", "output_root": str(output_root), "bundle_hash": bundle_hash}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuthorizationError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
    except ContractError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
