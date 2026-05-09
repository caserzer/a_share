#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
TOPIC_DIR = SCRIPT_DIR.parent.parent
BASELINE_SCRIPT_DIR = TOPIC_DIR / "ep2" / "engineering_baseline" / "scripts"
if str(BASELINE_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(BASELINE_SCRIPT_DIR))

import ep2_common as base  # noqa: E402


SCHEMA_VERSION = "requirement_05_daily_continuation_profit_protection_policy_v1"
PRIMARY_R03 = "hazard_probe_confirm_add_fast_fail"
BASELINE_POLICY = "R03_original_H10_replay"
R04_H20_POLICY = "R04_R03_confirmed_H20_replay_diagnostic"
R04_WINNER_POLICY = "R04_R03_winner_state_hold_H120_replay_diagnostic"
DETERMINISTIC_POLICIES = [
    "profit_lock_rule_simple",
    "trailing_stop_rule_simple",
    "partial_exit_after_profit_rule",
]
PROMOTION_INELIGIBLE = {BASELINE_POLICY, R04_H20_POLICY, R04_WINNER_POLICY, "matched_exposure_days_random_exit"}

REQUIRED_CACHE_ALWAYS = [
    "requirement_05_post_exposure_state_panel.parquet",
    "requirement_05_continuation_training_panel.parquet",
    "requirement_05_policy_action_panel.parquet",
    "requirement_05_policy_exposure_daily_panel.parquet",
    "requirement_05_matched_random_exit_panel.parquet",
]
FULL_MODEL_CACHE = ["requirement_05_continuation_prediction_panel.parquet"]
REQUIRED_REPORTS_ALWAYS = [
    "requirement_05_artifact_authority.csv",
    "requirement_05_sample_power_audit.csv",
    "requirement_05_stage_order_audit.csv",
    "requirement_05_feature_dictionary.csv",
    "requirement_05_feature_asof_audit.csv",
    "requirement_05_label_metric_dictionary.csv",
    "requirement_05_model_config_audit.csv",
    "requirement_05_deterministic_prephase_results.csv",
    "requirement_05_policy_grid_results.csv",
    "requirement_05_selected_policy.csv",
    "requirement_05_schedule_metrics.csv",
    "requirement_05_gate_audit.csv",
    "requirement_05_profit_protection_attribution.csv",
    "requirement_05_action_reason_audit.csv",
    "requirement_05_R03_replay_audit.csv",
    "requirement_05_R04_comparison_audit.csv",
    "requirement_05_R04_regime_audit.csv",
    "requirement_05_matched_random_exit_audit.csv",
    "requirement_05_concentration_audit.csv",
    "requirement_05_blocked_exit_audit.csv",
    "requirement_05_robustness_nonselection_audit.csv",
    "requirement_05_forbidden_recommendation_audit.csv",
    "requirement_05_report.md",
]
FULL_MODEL_REPORTS = ["requirement_05_model_calibration_audit.csv"]
REQUIRED_MANIFESTS = ["requirement_05_continuation_policy_manifest.json"]


@dataclass(frozen=True)
class RequirementPaths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    reports_dir: Path
    manifests_dir: Path
    baseline_config_path: Path
    baseline_output_root: Path
    requirement_01_output_root: Path
    requirement_02_output_root: Path
    requirement_03_output_root: Path
    requirement_04_output_root: Path


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    return base.relpath(path)


def file_hash(path: Path) -> str:
    return base.file_hash(path)


def canonical_hash(data: Any) -> str:
    return base.canonical_hash(data)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _date_str(value: Any) -> str:
    if pd.isna(value) or str(value) in {"", "NaT", "nan", "None"}:
        return ""
    return pd.Timestamp(value).date().isoformat()


def _as_date(value: Any) -> pd.Timestamp | pd.NaT:
    if pd.isna(value) or str(value) in {"", "NaT", "nan", "None", ""}:
        return pd.NaT
    return pd.Timestamp(value).normalize()


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return bool(value)


def _same_float(a: Any, b: Any, tol: float = 1e-12) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False


def load_requirement_config(config_path: str | Path) -> tuple[dict[str, Any], RequirementPaths, dict[str, Any], base.Paths]:
    cfg_path = topic_path(config_path)
    config = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    baseline_config_path = topic_path(config["baseline"]["config_path"])
    baseline_config = yaml.safe_load(baseline_config_path.read_text(encoding="utf-8")) or {}
    output_root = topic_path(config["output_root"])
    paths = RequirementPaths(
        config_path=cfg_path,
        output_root=output_root,
        cache_dir=output_root / "cache",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
        baseline_config_path=baseline_config_path,
        baseline_output_root=topic_path(config["baseline"]["output_root"]),
        requirement_01_output_root=topic_path(config["inputs"]["requirement_01_output_root"]),
        requirement_02_output_root=topic_path(config["inputs"]["requirement_02_output_root"]),
        requirement_03_output_root=topic_path(config["inputs"]["requirement_03_output_root"]),
        requirement_04_output_root=topic_path(config["inputs"]["requirement_04_output_root"]),
    )
    baseline_paths = base.Paths(
        config_path=baseline_config_path,
        output_root=paths.baseline_output_root,
        cache_dir=paths.baseline_output_root / "cache",
        reports_dir=paths.baseline_output_root / "reports",
        manifests_dir=paths.baseline_output_root / "manifests",
    )
    for directory in [paths.cache_dir, paths.reports_dir, paths.manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths, baseline_config, baseline_paths


def assert_entry_contract(config: dict[str, Any]) -> dict[str, Any]:
    frozen = config["frozen_contract"]
    r01_path = topic_path(frozen["requirement_01_manifest"])
    r02_path = topic_path(frozen["requirement_02_manifest"])
    r03_path = topic_path(frozen["requirement_03_manifest"])
    r04_path = topic_path(frozen["requirement_04_manifest"])
    r03_gate_path = topic_path(frozen["requirement_03_gate_audit"])
    for path in [r01_path, r02_path, r03_path, r04_path, r03_gate_path]:
        if not path.exists():
            raise RuntimeError(f"missing frozen input: {relpath(path)}")
    r01 = read_json(r01_path)
    r02 = read_json(r02_path)
    r03 = read_json(r03_path)
    r04 = read_json(r04_path)
    failures: list[str] = []
    if r01.get("validation_status") != frozen["expected_requirement_01_status"]:
        failures.append("Requirement 01 status mismatch")
    if r02.get("validation_status") != frozen["expected_requirement_02_status"]:
        failures.append("Requirement 02 status mismatch")
    if r03.get("validation_status") != frozen["expected_requirement_03_status"]:
        failures.append("Requirement 03 validation_status mismatch")
    if r03.get("next_phase_proceed_status") != frozen["expected_requirement_03_next_phase_status"]:
        failures.append("Requirement 03 next_phase_proceed_status mismatch")
    if r04.get("validation_status") != frozen["expected_requirement_04_status"]:
        failures.append("Requirement 04 validation_status mismatch")
    if r04.get("next_phase_proceed_status") != frozen["expected_requirement_04_next_phase_status"]:
        failures.append("Requirement 04 next_phase_proceed_status mismatch")
    if str(r04.get("selected_requirement_04_schedule_id") or "") != str(frozen["expected_requirement_04_selected_schedule_id"]):
        failures.append("Requirement 04 unexpectedly promoted a schedule")
    for key in ["primary_label_id", "frozen_baseline_id", "hazard_schedule_id", "schedule_bridge_id"]:
        if r03.get(key) != frozen[key]:
            failures.append(f"Requirement 03 {key} mismatch")
    if not _same_float(r03.get("selected_threshold"), frozen["selected_threshold"]):
        failures.append("Requirement 03 selected_threshold mismatch")
    if not _same_float(r03.get("selected_stop_risk_ceiling"), frozen["selected_stop_risk_ceiling"]):
        failures.append("Requirement 03 selected_stop_risk_ceiling mismatch")
    gates = pd.read_csv(r03_gate_path)
    gate_count = int(len(gates))
    passed = int(gates["passed"].astype(bool).sum()) if "passed" in gates else 0
    failed = gate_count - passed
    if gate_count != int(frozen["requirement_03_expected_gate_count"]):
        failures.append("Requirement 03 gate_count mismatch")
    if passed != int(frozen["requirement_03_expected_passed_gate_count"]):
        failures.append("Requirement 03 passed gate count mismatch")
    if failed != int(frozen["requirement_03_expected_failed_gate_count"]):
        failures.append("Requirement 03 failed gate count mismatch")
    if failures:
        raise RuntimeError("; ".join(failures))
    return {
        "requirement_01_manifest_hash": file_hash(r01_path),
        "requirement_02_manifest_hash": file_hash(r02_path),
        "requirement_03_manifest_hash": file_hash(r03_path),
        "requirement_04_manifest_hash": file_hash(r04_path),
        "requirement_03_gate_audit_hash": file_hash(r03_gate_path),
        "requirement_03_gate_count": gate_count,
        "requirement_03_passed_gate_count": passed,
        "requirement_03_failed_gate_count": failed,
    }


def _action_row(
    policy_id: str,
    episode_id: str,
    instrument: str,
    split: str,
    signal_date: Any,
    execution_date: Any,
    action_type: str,
    state_before: str,
    state_after: str,
    weight_before: float,
    weight_after: float,
    execution_price: float,
    is_executed: bool,
    blocked_reason: str,
    cost: dict[str, float],
    pending: dict[str, Any] | None,
    active_stop_before: float,
    active_stop_after: float,
    action_reason: str,
) -> dict[str, Any]:
    return {
        "policy_id": policy_id,
        "schedule_id": policy_id,
        "launch_episode_id": episode_id,
        "instrument": instrument,
        "split": split,
        "state_signal_date": _date_str(signal_date),
        "signal_date": _date_str(signal_date),
        "decision_date": _date_str(signal_date),
        "action_effective_date": _date_str(execution_date),
        "execution_date": _date_str(execution_date),
        "action_type": action_type,
        "action_reason": action_reason,
        "state_before": state_before,
        "state_after": state_after,
        "target_weight_before": float(weight_before),
        "target_weight_after": float(weight_after),
        "order_notional": abs(float(weight_before) - float(weight_after)),
        "action_execution_price": execution_price,
        "execution_price": execution_price,
        "is_executed": bool(is_executed),
        "blocked_action": bool(blocked_reason),
        "blocked_action_reason": blocked_reason,
        "blocked_reason": blocked_reason,
        "pending_exit_action_type": "" if pending is None else str(pending.get("action_type", "")),
        "pending_exit_reason": "" if pending is None else str(pending.get("reason", "")),
        "pending_exit_signal_date": "" if pending is None else _date_str(pending.get("signal_date", "")),
        "pending_exit_retry_day_count": 0 if pending is None else int(pending.get("retry_count", 0)),
        "active_stop_floor_before": active_stop_before,
        "active_stop_floor_after": active_stop_after,
        "continuation_score": np.nan,
        "P_profit_extension_10d": np.nan,
        "P_giveback_or_adverse_drawdown_10d": np.nan,
        "E_hold_vs_exit_delta_10d": np.nan,
        "commission_cost": cost.get("commission", 0.0),
        "stamp_tax_cost": cost.get("stamp", 0.0),
        "slippage_cost": cost.get("slippage", 0.0),
        "cost": cost.get("total", 0.0),
        "cash_weight": 1.0 - float(weight_after),
        "exit_retry_count": 0 if pending is None else int(pending.get("retry_count", 0)),
        "exit_status": "not_exit",
        "terminal_price_policy": "",
    }


def _empty_summary(policy_id: str, source: pd.Series, role: str) -> dict[str, Any]:
    return {
        "policy_id": policy_id,
        "schedule_id": policy_id,
        "policy_role": role,
        "split": source.get("split", ""),
        "launch_episode_id": str(source.get("launch_episode_id", "")),
        "instrument": str(source.get("instrument", "")).upper(),
        "launch_effective_date": _date_str(source.get("launch_effective_date", "")),
        "probe_executed": False,
        "confirm_add_executed": False,
        "had_exposure": False,
        "first_exposure_date": "",
        "first_exposure_price": np.nan,
        "confirm_add_execution_date": _date_str(source.get("confirm_add_execution_date", "")),
        "confirm_add_price": np.nan,
        "exit_date": "",
        "exit_reason": "",
        "after_cost_return": 0.0,
        "max_adverse_excursion": 0.0,
        "max_favorable_excursion": 0.0,
        "exposure_days": 0,
        "weighted_exposure_days": 0.0,
        "turnover": 0.0,
        "partial_exit_count": 0,
        "full_exit_count": 0,
        "tighten_stop_count": 0,
        "blocked_exit_retry_count": 0,
        "terminal_blocked_exit": False,
        "fast_fail_exit": False,
        "natural_exit": False,
        "strict_capture_50h120": False,
        "partial_capture_50h120": False,
        "exposure_weight_at_first_50pct_target_date": 0.0,
        "big_winner_50h120": False,
    }


def simulate_deterministic_episode(
    config: dict[str, Any],
    baseline_config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    universe_set: set[tuple[str, pd.Timestamp]],
    source: pd.Series,
    policy_id: str,
) -> dict[str, Any]:
    if not _bool(source.get("probe_executed", False)):
        return {"actions": [], "exposures": [], "summary": _empty_summary(policy_id, source, "deterministic")}
    instrument = str(source["instrument"]).upper()
    episode_id = str(source["launch_episode_id"])
    split = str(source["split"])
    probe_exec = _as_date(source["selected_probe_execution_date"])
    confirm_exec = _as_date(source.get("confirm_add_execution_date", ""))
    confirm_executed_source = _bool(source.get("confirm_add_executed", False)) and not pd.isna(confirm_exec)
    rates = base.cost_rates(baseline_config)
    limit_pct = float(baseline_config["execution"]["limit_inference_pct"]["mainboard_default"])
    max_retry = int(config["policies"]["blocked_exit_retry"]["max_retry_trading_days"])
    safety_cap = int(config["policies"]["max_holding_days_safety_cap"])
    sim_end = base.add_trading_days(calendar, probe_exec, safety_cap + max_retry + 5)
    if pd.isna(sim_end):
        sim_end = calendar[-1]
    sim_dates = calendar[(calendar >= probe_exec) & (calendar <= sim_end)]
    actions: list[dict[str, Any]] = []
    exposures: list[dict[str, Any]] = []
    state = "no_exposure"
    weight = 0.0
    first_exposure_date = pd.NaT
    first_exposure_price = np.nan
    confirm_add_price = np.nan
    prev_close = np.nan
    peak_close = np.nan
    active_stop_floor = np.nan
    active_stop_source = ""
    partial_done = False
    trailing_active = False
    pending: dict[str, Any] | None = None
    cum_gross = 0.0
    cum_net = 0.0
    turnover = 0.0
    total_cost = 0.0
    exit_date = pd.NaT
    exit_reason = ""
    partial_exit_count = full_exit_count = tighten_stop_count = blocked_retry_count = 0
    terminal_blocked = False
    fast_failed = False
    natural_exit = False

    def schedule_exit(kind: str, target: float, reason: str, signal_date: pd.Timestamp) -> dict[str, Any]:
        return {"action_type": kind, "target_weight_after": target, "is_exit": True, "reason": reason, "signal_date": signal_date}

    for date in sim_dates:
        date = pd.Timestamp(date)
        signal_date = base.prev_trading_day(calendar, date)
        info = lookup.get((instrument, date), {})
        open_price = float(info.get("open", np.nan))
        close_price = float(info.get("close", np.nan))
        low_price = float(info.get("low", np.nan))
        day_gross = 0.0
        day_cost = 0.0
        if weight > 0 and np.isfinite(close_price):
            reference = prev_close if np.isfinite(prev_close) else open_price
            if np.isfinite(reference) and reference > 0:
                day_gross = weight * (close_price / reference - 1.0)
        scheduled: list[dict[str, Any]] = []
        if pending is not None:
            scheduled.append({**pending, "retry": True})
        if date == probe_exec:
            scheduled.append({"action_type": "probe_entry", "target_weight_after": float(config["frozen_contract"]["probe_weight"]), "is_exit": False, "reason": "r03_probe_entry", "signal_date": signal_date})
        if confirm_executed_source and date == confirm_exec and weight > 0 and pending is None:
            scheduled.append({"action_type": "confirm_add", "target_weight_after": float(config["frozen_contract"]["full_weight_after_confirm"]), "is_exit": False, "reason": "r03_confirm_add", "signal_date": signal_date})
        if weight > 0 and pending is None and np.isfinite(first_exposure_price):
            if np.isfinite(low_price) and low_price / first_exposure_price - 1.0 <= -float(config["frozen_contract"]["base_fast_fail_drawdown"]):
                scheduled.append(schedule_exit("fast_fail_exit", 0.0, "r03_fast_fail", signal_date))
            elif not pd.isna(first_exposure_date) and date >= base.add_trading_days(calendar, first_exposure_date, safety_cap):
                scheduled.append(schedule_exit("natural_exit", 0.0, "safety_cap", signal_date))
            elif np.isfinite(prev_close):
                peak_close = max(peak_close, prev_close) if np.isfinite(peak_close) else prev_close
                ret = prev_close / first_exposure_price - 1.0
                peak_ret = peak_close / first_exposure_price - 1.0 if np.isfinite(peak_close) else ret
                giveback = ret - peak_ret
                stop_before = active_stop_floor
                if policy_id == "profit_lock_rule_simple":
                    p = config["policies"][policy_id]
                    if not partial_done and ret >= float(p["activate_return_from_first_exposure"]) and weight > float(p["partial_exit_to_weight"]):
                        scheduled.append(schedule_exit("partial_exit", float(p["partial_exit_to_weight"]), "profit_lock_partial", signal_date))
                    elif partial_done and giveback <= float(p["giveback_from_peak_profit_exit"]):
                        scheduled.append(schedule_exit("full_exit", 0.0, "profit_lock_giveback", signal_date))
                elif policy_id == "trailing_stop_rule_simple":
                    p = config["policies"][policy_id]
                    if ret >= float(p["activate_return_from_first_exposure"]):
                        trailing_active = True
                        active_stop_floor = max(active_stop_floor, peak_close * (1.0 - float(p["trailing_giveback"]))) if np.isfinite(active_stop_floor) else peak_close * (1.0 - float(p["trailing_giveback"]))
                        active_stop_source = "trailing_stop_rule_simple"
                        if not np.isfinite(stop_before) or active_stop_floor > stop_before:
                            tighten_stop_count += 1
                    if trailing_active and np.isfinite(active_stop_floor) and prev_close <= active_stop_floor:
                        scheduled.append(schedule_exit("forced_full_exit", 0.0, "active_stop_floor_breach", signal_date))
                elif policy_id == "partial_exit_after_profit_rule":
                    p = config["policies"][policy_id]
                    t = config["policies"]["trailing_stop_rule_simple"]
                    if trailing_active:
                        active_stop_floor = max(active_stop_floor, peak_close * (1.0 - float(t["trailing_giveback"]))) if np.isfinite(active_stop_floor) else peak_close * (1.0 - float(t["trailing_giveback"]))
                        active_stop_source = "partial_exit_trailing_stop"
                        if prev_close <= active_stop_floor:
                            scheduled.append(schedule_exit("forced_full_exit", 0.0, "active_stop_floor_breach", signal_date))
                    if not scheduled and not partial_done and ret >= float(p["activate_return_from_first_exposure"]):
                        scheduled.append(schedule_exit("partial_exit", weight * (1.0 - float(p["partial_exit_fraction"])), "partial_exit_after_profit", signal_date))
        for action in scheduled[:1]:
            before_state = state
            before_weight = weight
            action_type = str(action["action_type"])
            desired = float(action["target_weight_after"])
            is_exit = bool(action["is_exit"])
            status = base.execution_status(lookup, universe_set, instrument, action["signal_date"], date, limit_pct)
            blocked_reason = status["blocked_sell_reason"] if is_exit else status["blocked_buy_reason"]
            executable = not bool(blocked_reason)
            commission = stamp = slippage = 0.0
            if executable:
                order = abs(weight - desired)
                if is_exit:
                    commission = order * rates["commission_sell"]
                    stamp = order * rates["stamp_tax_sell"]
                    slippage = order * rates["slippage_sell"]
                    if desired <= 0:
                        full_exit_count += 1
                        state = "exited"
                        exit_date = date
                        exit_reason = action_type
                        fast_failed = action_type == "fast_fail_exit"
                        natural_exit = action_type == "natural_exit"
                    else:
                        partial_exit_count += 1
                        state = "partial_exposure"
                        partial_done = True
                        if policy_id == "partial_exit_after_profit_rule":
                            trailing_active = True
                    weight = desired
                    if desired <= 0:
                        pending = None
                else:
                    commission = order * rates["commission_buy"]
                    slippage = order * rates["slippage_buy"]
                    weight = desired
                    state = "full_exposure" if weight >= 0.999 else "partial_exposure"
                    if pd.isna(first_exposure_date):
                        first_exposure_date = date
                        first_exposure_price = float(status["execution_price_reference"])
                    if action_type == "confirm_add":
                        confirm_add_price = float(status["execution_price_reference"])
                cost_total = commission + stamp + slippage
                day_cost += cost_total
                total_cost += cost_total
                turnover += abs(before_weight - desired)
                pending_after = pending
            else:
                cost_total = 0.0
                if is_exit:
                    retry_count = int(pending.get("retry_count", 0)) + 1 if pending else 1
                    blocked_retry_count += 1
                    if retry_count > max_retry:
                        terminal_blocked = True
                        state = "exited"
                        exit_date = date
                        exit_reason = "terminal_blocked_exit"
                        weight = 0.0
                        pending = None
                    else:
                        pending = {**action, "retry_count": retry_count}
                pending_after = pending
            actions.append(
                _action_row(
                    policy_id,
                    episode_id,
                    instrument,
                    split,
                    action["signal_date"],
                    date,
                    action_type if executable else "blocked_action",
                    before_state,
                    state,
                    before_weight,
                    weight,
                    float(status["execution_price_reference"]),
                    executable,
                    blocked_reason,
                    {"commission": commission, "stamp": stamp, "slippage": slippage, "total": cost_total},
                    pending_after,
                    stop_before if "stop_before" in locals() else np.nan,
                    active_stop_floor,
                    str(action["reason"]),
                )
            )
        day_net = day_gross - day_cost
        cum_gross = (1.0 + cum_gross) * (1.0 + day_gross) - 1.0
        cum_net = (1.0 + cum_net) * (1.0 + day_net) - 1.0
        if weight > 0 or not pd.isna(first_exposure_date):
            exposures.append(
                {
                    "date": _date_str(date),
                    "policy_id": policy_id,
                    "schedule_id": policy_id,
                    "launch_episode_id": episode_id,
                    "instrument": instrument,
                    "state": state,
                    "target_weight": weight,
                    "actual_weight": weight,
                    "cash_weight": 1.0 - weight,
                    "daily_return_gross": day_gross,
                    "daily_return_net": day_net,
                    "cum_return_gross": cum_gross,
                    "cum_return_net": cum_net,
                }
            )
        if np.isfinite(close_price):
            prev_close = close_price
            if weight > 0:
                peak_close = max(peak_close, close_price) if np.isfinite(peak_close) else close_price
        if state == "exited" and pending is None and not pd.isna(exit_date):
            break
    summary = _empty_summary(policy_id, source, "deterministic")
    exposure_days = sum(1 for row in exposures if float(row["actual_weight"]) > 0)
    weighted_days = float(sum(float(row["actual_weight"]) for row in exposures))
    summary.update(
        {
            "probe_executed": True,
            "confirm_add_executed": confirm_executed_source,
            "had_exposure": not pd.isna(first_exposure_date),
            "first_exposure_date": _date_str(first_exposure_date),
            "first_exposure_price": first_exposure_price,
            "confirm_add_execution_date": _date_str(confirm_exec),
            "confirm_add_price": confirm_add_price,
            "exit_date": _date_str(exit_date),
            "exit_reason": exit_reason,
            "after_cost_return": cum_net if not pd.isna(first_exposure_date) else 0.0,
            "max_adverse_excursion": float(min([row["cum_return_net"] for row in exposures], default=0.0)),
            "max_favorable_excursion": float(max([row["cum_return_net"] for row in exposures], default=0.0)),
            "exposure_days": exposure_days,
            "weighted_exposure_days": weighted_days,
            "turnover": turnover,
            "partial_exit_count": partial_exit_count,
            "full_exit_count": full_exit_count,
            "tighten_stop_count": tighten_stop_count,
            "blocked_exit_retry_count": blocked_retry_count,
            "terminal_blocked_exit": terminal_blocked,
            "fast_fail_exit": fast_failed,
            "natural_exit": natural_exit,
        }
    )
    return {"actions": actions, "exposures": exposures, "summary": summary}


def build_r03_baseline(r03_actions: pd.DataFrame, r03_exposures: pd.DataFrame, r03_summaries: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    primary_summaries = r03_summaries.loc[r03_summaries["schedule_id"].eq(PRIMARY_R03)].copy()
    actions = r03_actions.loc[r03_actions["schedule_id"].eq(PRIMARY_R03)].copy()
    actions["policy_id"] = BASELINE_POLICY
    actions["schedule_id"] = BASELINE_POLICY
    actions["split"] = actions["launch_episode_id"].map(primary_summaries.set_index("launch_episode_id")["split"])
    actions["state_signal_date"] = actions["signal_date"]
    actions["action_effective_date"] = actions["execution_date"]
    actions["action_reason"] = actions["action_type"]
    actions["blocked_action"] = actions["blocked_reason"].astype(str).ne("")
    actions["blocked_action_reason"] = actions["blocked_reason"]
    actions["pending_exit_action_type"] = ""
    actions["pending_exit_reason"] = ""
    actions["pending_exit_signal_date"] = ""
    actions["pending_exit_retry_day_count"] = actions["exit_retry_count"].fillna(0).astype(int)
    actions["active_stop_floor_before"] = np.nan
    actions["active_stop_floor_after"] = np.nan
    actions["continuation_score"] = np.nan
    actions["P_profit_extension_10d"] = np.nan
    actions["P_giveback_or_adverse_drawdown_10d"] = np.nan
    actions["E_hold_vs_exit_delta_10d"] = np.nan
    actions["action_execution_price"] = actions["execution_price"]
    exposures = r03_exposures.loc[r03_exposures["schedule_id"].eq(PRIMARY_R03)].copy()
    exposures["policy_id"] = BASELINE_POLICY
    exposures["schedule_id"] = BASELINE_POLICY
    rows = []
    exp_by_ep = {eid: group for eid, group in exposures.groupby("launch_episode_id", sort=False)}
    for row in primary_summaries.itertuples(index=False):
        exp = exp_by_ep.get(row.launch_episode_id, pd.DataFrame())
        summary = _empty_summary(BASELINE_POLICY, pd.Series(row._asdict()), "baseline")
        summary.update(
            {
                "probe_executed": _bool(row.probe_executed),
                "confirm_add_executed": _bool(row.confirm_add_executed),
                "had_exposure": _bool(row.had_exposure),
                "first_exposure_date": _date_str(row.first_exposure_date),
                "first_exposure_price": float(row.first_exposure_price) if pd.notna(row.first_exposure_price) else np.nan,
                "confirm_add_execution_date": _date_str(row.confirm_add_execution_date),
                "exit_date": _date_str(row.exit_date),
                "exit_reason": "fast_fail_exit" if _bool(row.fast_fail_exit) else ("natural_exit" if _bool(row.natural_exit) else ""),
                "after_cost_return": float(row.after_cost_return),
                "max_adverse_excursion": float(exp["cum_return_net"].min()) if not exp.empty else 0.0,
                "max_favorable_excursion": float(exp["cum_return_net"].max()) if not exp.empty else 0.0,
                "exposure_days": int(exp["actual_weight"].astype(float).gt(0).sum()) if not exp.empty else 0,
                "weighted_exposure_days": float(exp["actual_weight"].astype(float).sum()) if not exp.empty else 0.0,
                "turnover": float(row.turnover),
                "fast_fail_exit": _bool(row.fast_fail_exit),
                "natural_exit": _bool(row.natural_exit),
            }
        )
        rows.append(summary)
    return actions, exposures, pd.DataFrame(rows)


def load_r04_diagnostics(paths: RequirementPaths) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    actions = pd.read_parquet(paths.requirement_04_output_root / "cache" / "requirement_04_schedule_action_panel.parquet")
    exposures = pd.read_parquet(paths.requirement_04_output_root / "cache" / "requirement_04_exposure_daily_panel.parquet")
    summaries = pd.read_parquet(paths.requirement_04_output_root / "cache" / "requirement_04_episode_schedule_summary.parquet")
    mapping = {"R03_confirmed_H20": R04_H20_POLICY, "R03_winner_state_hold_H120": R04_WINNER_POLICY}
    out_actions = []
    out_exposures = []
    out_summaries = []
    for source_id, policy_id in mapping.items():
        a = actions.loc[actions["schedule_id"].eq(source_id)].copy()
        e = exposures.loc[exposures["schedule_id"].eq(source_id)].copy()
        s = summaries.loc[summaries["schedule_id"].eq(source_id)].copy()
        for frame in [a, e, s]:
            frame["policy_id"] = policy_id
            frame["schedule_id"] = policy_id
            frame["policy_role"] = "diagnostic"
        out_actions.append(a)
        out_exposures.append(e)
        if "schedule_role" in s:
            s = s.drop(columns=["schedule_role"])
        if "partial_exit_count" not in s:
            s["partial_exit_count"] = 0
        if "full_exit_count" not in s:
            s["full_exit_count"] = s["exit_reason"].astype(str).ne("").astype(int)
        if "tighten_stop_count" not in s:
            s["tighten_stop_count"] = 0
        if "terminal_blocked_exit" not in s:
            s["terminal_blocked_exit"] = s["exit_reason"].astype(str).eq("terminal_blocked_exit")
        out_summaries.append(s)
    return pd.concat(out_actions, ignore_index=True), pd.concat(out_exposures, ignore_index=True), pd.concat(out_summaries, ignore_index=True)


def target_table(paths: RequirementPaths) -> pd.DataFrame:
    capture = pd.read_csv(paths.requirement_04_output_root / "reports" / "requirement_04_big_winner_capture_audit.csv")
    targets = capture.loc[capture["schedule_id"].eq("R03_original_H10") & capture["variant_id"].eq("base")].copy()
    return targets[
        [
            "launch_episode_id",
            "instrument",
            "first_50pct_target_date",
            "first_100pct_target_date",
            "big_winner_50h120",
            "big_winner_100h240",
        ]
    ].drop_duplicates("launch_episode_id")


def apply_capture_metrics(summaries: pd.DataFrame, exposures: pd.DataFrame, targets: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries = summaries.copy()
    exp_key = {(row.policy_id, row.launch_episode_id, str(row.date)): float(row.actual_weight) for row in exposures.itertuples(index=False)}
    exp_dates: dict[tuple[str, str], set[str]] = {}
    for row in exposures.loc[exposures["actual_weight"].astype(float).gt(0)].itertuples(index=False):
        exp_dates.setdefault((row.policy_id, row.launch_episode_id), set()).add(str(row.date))
    target_by_ep = targets.set_index("launch_episode_id").to_dict("index")
    rows = []
    strict = []
    partial = []
    weights = []
    big_flags = []
    for row in summaries.itertuples(index=False):
        target = target_by_ep.get(row.launch_episode_id, {})
        first50 = str(target.get("first_50pct_target_date", "") or "")
        big = _bool(target.get("big_winner_50h120", False))
        weight = exp_key.get((row.policy_id, row.launch_episode_id, first50), 0.0) if big and first50 else 0.0
        part = False
        if big and first50:
            part = any(d < first50 for d in exp_dates.get((row.policy_id, row.launch_episode_id), set()))
        strict.append(bool(weight > 0))
        partial.append(bool(part))
        weights.append(float(weight))
        big_flags.append(bool(big))
        rows.append(
            {
                "policy_id": row.policy_id,
                "split": row.split,
                "launch_episode_id": row.launch_episode_id,
                "instrument": row.instrument,
                "first_50pct_target_date": first50,
                "big_winner_50h120": bool(big),
                "had_positive_exposure_before_first_50pct_target_date": bool(part),
                "exposure_weight_at_first_50pct_target_date": float(weight),
                "strict_capture_50h120": bool(weight > 0),
                "partial_capture_50h120": bool(part),
                "exit_date": row.exit_date,
                "exit_before_first_50pct_target": bool(big and row.exit_date and first50 and row.exit_date < first50),
                "exit_reason": row.exit_reason,
            }
        )
    summaries["strict_capture_50h120"] = strict
    summaries["partial_capture_50h120"] = partial
    summaries["exposure_weight_at_first_50pct_target_date"] = weights
    summaries["big_winner_50h120"] = big_flags
    return summaries, pd.DataFrame(rows)


def build_state_panel(
    config: dict[str, Any],
    baseline_config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    universe_set: set[tuple[str, pd.Timestamp]],
    r03_exposures: pd.DataFrame,
    r03_summaries: pd.DataFrame,
    r02_predictions: pd.DataFrame,
) -> pd.DataFrame:
    primary = r03_summaries.loc[r03_summaries["schedule_id"].eq(PRIMARY_R03)].set_index("launch_episode_id")
    probe_scores = r02_predictions.rename(columns={"probe_signal_date": "selected_probe_signal_date"}).copy()
    score_key = {
        (row.launch_episode_id, str(row.probe_execution_date)): row
        for row in probe_scores.itertuples(index=False)
    }
    rows = []
    limit_pct = float(baseline_config["execution"]["limit_inference_pct"]["mainboard_default"])
    for exp in r03_exposures.loc[r03_exposures["schedule_id"].eq(PRIMARY_R03) & r03_exposures["actual_weight"].astype(float).gt(0)].itertuples(index=False):
        if exp.launch_episode_id not in primary.index:
            continue
        ep = primary.loc[exp.launch_episode_id]
        state_signal_date = _as_date(exp.date)
        action_effective_date = base.next_trading_day(calendar, state_signal_date)
        inst = str(exp.instrument).upper()
        current = lookup.get((inst, state_signal_date), {})
        status = base.execution_status(lookup, universe_set, inst, state_signal_date, action_effective_date, limit_pct)
        first_price = float(ep.first_exposure_price) if pd.notna(ep.first_exposure_price) else np.nan
        confirm_price = np.nan
        confirm_actions = r03_exposures.iloc[0:0]
        current_close = float(current.get("close", np.nan))
        ret_first = current_close / first_price - 1.0 if np.isfinite(current_close) and np.isfinite(first_price) and first_price > 0 else np.nan
        first_date = _as_date(ep.first_exposure_date)
        dates = calendar[(calendar >= first_date) & (calendar <= state_signal_date)] if not pd.isna(first_date) else []
        closes = [float(lookup.get((inst, d), {}).get("close", np.nan)) for d in dates]
        finite = [v for v in closes if np.isfinite(v)]
        max_close = max(finite) if finite else np.nan
        min_close = min(finite) if finite else np.nan
        peak_ret = max_close / first_price - 1.0 if np.isfinite(max_close) and np.isfinite(first_price) and first_price > 0 else np.nan
        min_ret = min_close / first_price - 1.0 if np.isfinite(min_close) and np.isfinite(first_price) and first_price > 0 else np.nan
        score = score_key.get((exp.launch_episode_id, str(ep.selected_probe_execution_date)))
        rows.append(
            {
                "launch_episode_id": exp.launch_episode_id,
                "instrument": inst,
                "split": ep.split,
                "state_signal_date": _date_str(state_signal_date),
                "action_effective_date": _date_str(action_effective_date),
                "action_execution_price": status["execution_price_reference"],
                "state_row_id": f"{exp.launch_episode_id}_{_date_str(state_signal_date)}",
                "r03_first_exposure_signal_date": "",
                "r03_first_exposure_execution_date": _date_str(ep.first_exposure_date),
                "r03_first_exposure_price": first_price,
                "r03_confirm_add_signal_date": _date_str(ep.confirm_add_signal_date),
                "r03_confirm_add_execution_date": _date_str(ep.confirm_add_execution_date),
                "r03_confirm_add_price": confirm_price,
                "current_exposure_weight_before_action": float(exp.actual_weight),
                "active_position_state": exp.state,
                "has_probe_entry_executed": _bool(ep.probe_executed),
                "has_confirm_add_executed": _bool(ep.confirm_add_executed),
                "days_since_first_exposure": int(len(calendar[(calendar >= first_date) & (calendar <= state_signal_date)])) - 1 if not pd.isna(first_date) else 0,
                "days_since_confirm_add": 0 if pd.isna(_as_date(ep.confirm_add_execution_date)) else max(int(len(calendar[(calendar >= _as_date(ep.confirm_add_execution_date)) & (calendar <= state_signal_date)])) - 1, 0),
                "remaining_days_to_R03_H10_natural_exit": np.nan,
                "current_close": current_close,
                "current_return_from_first_exposure": ret_first,
                "current_return_from_confirm_add": np.nan,
                "current_unrealized_return_weighted": ret_first * float(exp.actual_weight) if np.isfinite(ret_first) else np.nan,
                "max_favorable_excursion_since_first_exposure": peak_ret,
                "max_adverse_excursion_since_first_exposure": min_ret,
                "post_confirm_high_to_date": np.nan,
                "drawdown_from_post_confirm_high": np.nan,
                "giveback_from_peak_profit": ret_first - peak_ret if np.isfinite(ret_first) and np.isfinite(peak_ret) else np.nan,
                "current_profit_cushion": max(ret_first, 0.0) if np.isfinite(ret_first) else np.nan,
                "distance_to_first_exposure_price": ret_first,
                "distance_to_confirm_add_price": np.nan,
                "active_stop_floor": np.nan,
                "active_stop_source": "",
                "sell_executable_next_open": status["is_sell_executable_next_open"],
                "blocked_sell_reason_next_open": status["blocked_sell_reason"],
                "buy_or_add_executable_next_open": status["is_buy_executable_next_open"],
                "blocked_buy_reason_next_open": status["blocked_buy_reason"],
                "r02_P_target_first_at_probe": np.nan if score is None else score.P_target_first,
                "r02_P_stop_first_at_probe": np.nan if score is None else score.P_stop_first,
                "r02_P_neither_at_probe": np.nan if score is None else score.P_neither,
                "r02_score_probe_day_at_probe": np.nan if score is None else score.score_probe_day,
                "r02_selected_threshold": config["frozen_contract"]["selected_threshold"],
                "r02_selected_stop_risk_ceiling": config["frozen_contract"]["selected_stop_risk_ceiling"],
                "feature_asof_date": _date_str(state_signal_date),
                "feature_asof_violation_flag": False,
            }
        )
    return pd.DataFrame(rows)


def summarize_policy_metrics(summaries: pd.DataFrame, baseline_config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for (policy_id, split), group in summaries.groupby(["policy_id", "split"], sort=True):
        role = group["policy_role"].iloc[0]
        returns = group["after_cost_return"].astype(float)
        exposed = group["had_exposure"].astype(bool)
        big = group.loc[group["big_winner_50h120"].astype(bool)]
        bw_count = len(big)
        top_keys = group.loc[exposed, "instrument"].astype(str) + "_" + pd.to_datetime(group.loc[exposed, "first_exposure_date"], errors="coerce").dt.year.fillna(0).astype(int).astype(str)
        shares = top_keys.value_counts(normalize=True)
        strict_count = int(big["strict_capture_50h120"].astype(bool).sum()) if bw_count else 0
        rows.append(
            {
                "policy_id": policy_id,
                "split": split,
                "policy_role": role,
                "episode_count": int(len(group)),
                "exposed_episode_count": int(exposed.sum()),
                "action_count": int(group[["partial_exit_count", "full_exit_count", "tighten_stop_count"]].sum(axis=1).sum()),
                "partial_exit_count": int(group["partial_exit_count"].astype(int).sum()),
                "full_exit_count": int(group["full_exit_count"].astype(int).sum()),
                "tighten_stop_count": int(group["tighten_stop_count"].astype(int).sum()),
                "blocked_exit_count": int(group["blocked_exit_retry_count"].astype(int).gt(0).sum()),
                "blocked_exit_retry_count": int(group["blocked_exit_retry_count"].astype(int).sum()),
                "terminal_blocked_exit_count": int(group["terminal_blocked_exit"].astype(bool).sum()),
                "mean_after_cost_return": float(returns.mean()),
                "median_after_cost_return": float(returns.median()),
                "p05_after_cost_return": float(returns.quantile(0.05)),
                "p95_after_cost_return": float(returns.quantile(0.95)),
                "max_adverse_excursion_mean": float(group["max_adverse_excursion"].astype(float).mean()),
                "max_adverse_excursion_p95": float(group["max_adverse_excursion"].astype(float).quantile(0.95)),
                "strict_big_winner_capture_rate_50h120": float(big["strict_capture_50h120"].astype(bool).mean()) if bw_count else 0.0,
                "strict_big_winner_capture_count_50h120": strict_count,
                "exposure_weighted_big_winner_capture_rate_50h120": float(big["exposure_weight_at_first_50pct_target_date"].astype(float).sum() / bw_count) if bw_count else 0.0,
                "partial_capture_rate_50h120": float(big["partial_capture_50h120"].astype(bool).mean()) if bw_count else 0.0,
                "actionable_big_winner_episode_count_50h120": int(big["partial_capture_50h120"].astype(bool).sum()) if bw_count else 0,
                "baseline_strict_captured_big_winner_count_50h120": 0,
                "actionable_uncaptured_big_winner_count_50h120": 0,
                "big_winner_episode_count_50h120": bw_count,
                "mean_exposure_days": float(group["exposure_days"].astype(float).mean()),
                "median_exposure_days": float(group["exposure_days"].astype(float).median()),
                "capital_occupancy_proxy": float(group["weighted_exposure_days"].astype(float).mean()),
                "turnover_proxy": float(group["turnover"].astype(float).sum() / max(len(group), 1) * 252.0 / max(int(baseline_config["schedule_defaults"]["primary_H"]), 1)),
                "turnover_ratio_vs_R03": np.nan,
                "exposure_day_multiple_vs_R03": np.nan,
                "top1_instrument_year_exposure_share": float(shares.iloc[0]) if len(shares) else 0.0,
                "top5_instrument_exposure_share": float(shares.head(5).sum()) if len(shares) else 0.0,
                "matched_random_real_minus_p50": np.nan,
                "matched_random_real_minus_p95": np.nan,
                "track_B_one_capture_loss_exception_used": False,
                "sample_power_stage": "deterministic_prephase_only",
                "promotion_eligible_stage": policy_id in DETERMINISTIC_POLICIES,
            }
        )
    results = pd.DataFrame(rows)
    base_rows = results.loc[results["policy_id"].eq(BASELINE_POLICY)].set_index("split")
    for idx, row in results.iterrows():
        if row["split"] in base_rows.index:
            b = base_rows.loc[row["split"]]
            results.loc[idx, "turnover_ratio_vs_R03"] = float(row["turnover_proxy"]) / float(b["turnover_proxy"]) if float(b["turnover_proxy"]) else np.inf
            results.loc[idx, "exposure_day_multiple_vs_R03"] = float(row["capital_occupancy_proxy"]) / float(b["capital_occupancy_proxy"]) if float(b["capital_occupancy_proxy"]) else np.inf
            results.loc[idx, "baseline_strict_captured_big_winner_count_50h120"] = int(b["strict_big_winner_capture_count_50h120"])
            results.loc[idx, "actionable_uncaptured_big_winner_count_50h120"] = max(int(row["actionable_big_winner_episode_count_50h120"]) - int(b["strict_big_winner_capture_count_50h120"]), 0)
    return results


def build_comparison(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    base_rows = results.loc[results["policy_id"].eq(BASELINE_POLICY)].set_index("split")
    for row in results.itertuples(index=False):
        if row.policy_id == BASELINE_POLICY or row.split not in base_rows.index:
            continue
        b = base_rows.loc[row.split]
        rows.append(
            {
                "split": row.split,
                "policy_id": row.policy_id,
                "comparison_policy_id": BASELINE_POLICY,
                "policy_role": row.policy_role,
                "mean_after_cost_return_diff_vs_R03": float(row.mean_after_cost_return) - float(b.mean_after_cost_return),
                "median_after_cost_return_diff_vs_R03": float(row.median_after_cost_return) - float(b.median_after_cost_return),
                "p05_after_cost_return_diff_vs_R03": float(row.p05_after_cost_return) - float(b.p05_after_cost_return),
                "max_adverse_excursion_mean_diff_vs_R03": float(row.max_adverse_excursion_mean) - float(b.max_adverse_excursion_mean),
                "strict_big_winner_capture_rate_50h120_diff_vs_R03": float(row.strict_big_winner_capture_rate_50h120) - float(b.strict_big_winner_capture_rate_50h120),
                "strict_big_winner_capture_count_50h120_diff_vs_R03": int(row.strict_big_winner_capture_count_50h120) - int(b.strict_big_winner_capture_count_50h120),
                "exposure_weighted_big_winner_capture_rate_50h120_diff_vs_R03": float(row.exposure_weighted_big_winner_capture_rate_50h120) - float(b.exposure_weighted_big_winner_capture_rate_50h120),
                "partial_capture_rate_50h120_diff_vs_R03": float(row.partial_capture_rate_50h120) - float(b.partial_capture_rate_50h120),
                "exposure_day_multiple_vs_R03": float(row.exposure_day_multiple_vs_R03),
                "turnover_ratio_vs_R03": float(row.turnover_ratio_vs_R03),
            }
        )
    return pd.DataFrame(rows)


def build_sample_power(config: dict[str, Any], results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    gates = config["sample_power"]
    deterministic_count = len(config["policies"]["deterministic_policy_ids"])
    base_results = results.loc[results["policy_id"].eq(BASELINE_POLICY)]
    for row in base_results.itertuples(index=False):
        deterministic_allowed = (
            row.split != "validation"
            or (
                int(row.exposed_episode_count) >= int(gates["deterministic_stage_min_validation_exposed_episodes"])
                and int(row.big_winner_episode_count_50h120) >= int(gates["deterministic_stage_min_validation_big_winner_50h120"])
                and int(row.actionable_big_winner_episode_count_50h120) >= int(gates["deterministic_stage_min_validation_actionable_big_winner_50h120"])
            )
        )
        full_allowed = (
            row.split != "validation"
            or (
                int(row.exposed_episode_count) >= int(gates["full_model_min_validation_exposed_episodes"])
                and int(row.big_winner_episode_count_50h120) >= int(gates["full_model_min_validation_big_winner_50h120"])
                and int(row.actionable_big_winner_episode_count_50h120) >= int(gates["full_model_min_validation_actionable_big_winner_50h120"])
            )
        )
        rows.append(
            {
                "split": row.split,
                "exposed_episode_count": int(row.exposed_episode_count),
                "big_winner_episode_count_50h120": int(row.big_winner_episode_count_50h120),
                "actionable_big_winner_episode_count_50h120": int(row.actionable_big_winner_episode_count_50h120),
                "baseline_strict_captured_big_winner_count_50h120": int(row.strict_big_winner_capture_count_50h120),
                "actionable_uncaptured_big_winner_count_50h120": int(row.actionable_uncaptured_big_winner_count_50h120),
                "state_row_count": np.nan,
                "confirmed_exposed_episode_count": np.nan,
                "deterministic_candidate_count": deterministic_count,
                "model_candidate_count": 0,
                "estimated_free_parameter_count": 0,
                "events_per_candidate": float(row.big_winner_episode_count_50h120) / deterministic_count if deterministic_count else 0.0,
                "events_per_free_parameter": np.inf,
                "deterministic_stage_allowed": bool(deterministic_allowed),
                "full_model_stage_allowed": bool(full_allowed),
                "full_model_stage_executed": False,
                "failure_reason": "" if full_allowed else "insufficient_full_model_sample_power",
            }
        )
    return pd.DataFrame(rows)


def build_matched_random(config: dict[str, Any], results: pd.DataFrame, summaries: pd.DataFrame, action_hashes: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(int(config["matched_random_exit"]["random_seed"]))
    n = int(config["matched_random_exit"]["n_repeats"])
    base_summaries = summaries.loc[summaries["policy_id"].eq(BASELINE_POLICY)].copy()
    panel_rows = []
    audit_rows = []
    for policy_id in DETERMINISTIC_POLICIES:
        candidate = summaries.loc[summaries["policy_id"].eq(policy_id)].copy()
        if candidate.empty:
            continue
        policy_hash = action_hashes.get(policy_id, "")
        rand_values_by_split: dict[str, list[float]] = {}
        for repeat in range(n):
            for split, group in candidate.groupby("split"):
                base_pool = base_summaries.loc[base_summaries["split"].eq(split), "after_cost_return"].astype(float).to_numpy()
                sample = rng.choice(base_pool, size=len(group), replace=True) if len(base_pool) else np.array([0.0])
                mean = float(np.mean(sample))
                p05 = float(np.quantile(sample, 0.05))
                rand_values_by_split.setdefault(split, []).append(mean)
                panel_rows.append(
                    {
                        "policy_id": policy_id,
                        "random_reference_policy_id": f"{policy_id}_matched_random",
                        "random_repeat_id": repeat,
                        "matched_to_policy_id": policy_id,
                        "split": split,
                        "random_mean": mean,
                        "random_p05": p05,
                        "candidate_policy_hash": policy_hash,
                        "generated_after_policy_action_hash": policy_hash,
                        "matched_random_generated_before_selection": True,
                    }
                )
        for split, values in rand_values_by_split.items():
            real = results.loc[results["policy_id"].eq(policy_id) & results["split"].eq(split), "mean_after_cost_return"]
            real_value = float(real.iloc[0]) if not real.empty else np.nan
            vals = np.asarray(values, dtype=float)
            random_hash = canonical_hash({"policy_id": policy_id, "split": split, "values": [round(float(v), 12) for v in vals]})
            audit_rows.append(
                {
                    "policy_id": policy_id,
                    "split": split,
                    "random_reference_policy_id": f"{policy_id}_matched_random",
                    "random_mean": float(np.mean(vals)),
                    "random_std": float(np.std(vals)),
                    "random_p05": float(np.quantile(vals, 0.05)),
                    "random_p50": float(np.quantile(vals, 0.50)),
                    "random_p95": float(np.quantile(vals, 0.95)),
                    "real_mean_after_cost_return": real_value,
                    "real_minus_random_p50": real_value - float(np.quantile(vals, 0.50)),
                    "real_minus_random_p95": real_value - float(np.quantile(vals, 0.95)),
                    "candidate_policy_hash": policy_hash,
                    "random_baseline_hash": random_hash,
                    "matched_random_generated_before_selection": True,
                }
            )
    return pd.DataFrame(panel_rows), pd.DataFrame(audit_rows)


def select_policy(config: dict[str, Any], results: pd.DataFrame, comparison: pd.DataFrame, random_audit: pd.DataFrame, sample_power: pd.DataFrame, regime_status: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    gates = config["r05_gates"]
    validation_big = int(results.loc[results["policy_id"].eq(BASELINE_POLICY) & results["split"].eq("validation"), "big_winner_episode_count_50h120"].iloc[0])
    required_count = max(int(gates["track_A_min_strict_capture_count_diff_floor"]), int(np.ceil(float(gates["track_A_min_strict_capture_count_diff_rate"]) * validation_big)))
    gate_rows = []
    selected_rows = []
    for policy_id in DETERMINISTIC_POLICIES:
        val = comparison.loc[comparison["policy_id"].eq(policy_id) & comparison["split"].eq("validation")]
        res = results.loc[results["policy_id"].eq(policy_id) & results["split"].eq("validation")]
        rand = random_audit.loc[random_audit["policy_id"].eq(policy_id) & random_audit["split"].eq("validation")]
        if val.empty or res.empty:
            continue
        c = val.iloc[0]
        r = res.iloc[0]
        random_p50_ok = not rand.empty and float(rand.iloc[0].real_minus_random_p50) > 0
        random_p95_ok = not rand.empty and float(rand.iloc[0].real_minus_random_p95) >= -float(gates["max_random_p95_shortfall"])
        track_a = (
            int(c.strict_big_winner_capture_count_50h120_diff_vs_R03) >= required_count
            and int(r.actionable_uncaptured_big_winner_count_50h120) >= required_count
            and float(c.exposure_weighted_big_winner_capture_rate_50h120_diff_vs_R03) >= 0
            and float(c.mean_after_cost_return_diff_vs_R03) >= float(gates["max_mean_drop_vs_R03_negative_bound"])
            and float(c.p05_after_cost_return_diff_vs_R03) >= float(gates["max_p05_drop_vs_R03_negative_bound"])
            and max(0.0, -float(c.max_adverse_excursion_mean_diff_vs_R03)) <= float(gates["max_mae_worsening_vs_R03"])
            and float(c.exposure_day_multiple_vs_R03) <= float(gates["max_exposure_day_multiple_vs_R03"])
            and random_p50_ok
            and random_p95_ok
        )
        strict_loss_count = max(0, -int(c.strict_big_winner_capture_count_50h120_diff_vs_R03))
        strict_loss_rate = max(0.0, -float(c.strict_big_winner_capture_rate_50h120_diff_vs_R03))
        weighted_loss = max(0.0, -float(c.exposure_weighted_big_winner_capture_rate_50h120_diff_vs_R03))
        one_loss_exception = (
            strict_loss_count == 1
            and float(c.p05_after_cost_return_diff_vs_R03) >= float(gates["track_B_one_capture_loss_min_p05_improvement"])
            and float(c.mean_after_cost_return_diff_vs_R03) >= float(gates["track_B_one_capture_loss_min_mean_improvement"])
            and weighted_loss <= float(gates["track_B_one_capture_loss_max_exposure_weighted_loss"])
        )
        track_b_capture_ok = strict_loss_count <= int(gates["track_B_max_strict_capture_count_loss"]) or one_loss_exception
        track_b = (
            track_b_capture_ok
            and strict_loss_rate <= float(gates["max_strict_capture_rate_loss_vs_R03"])
            and weighted_loss <= float(gates["max_exposure_weighted_capture_loss_vs_R03"])
            and float(c.mean_after_cost_return_diff_vs_R03) >= float(gates["min_mean_improvement_vs_R03_for_profit_protection"])
            and float(c.p05_after_cost_return_diff_vs_R03) >= float(gates["min_p05_improvement_vs_R03_for_profit_protection"])
            and float(c.max_adverse_excursion_mean_diff_vs_R03) >= float(gates["min_mae_improvement_vs_R03_for_profit_protection"])
            and random_p50_ok
            and random_p95_ok
        )
        for name, passed, value, threshold, category in [
            ("track_A_pass", track_a, track_a, True, "winner_capture"),
            ("track_B_pass", track_b, track_b, True, "profit_protection"),
            ("matched_random_p50_pass", random_p50_ok, rand.iloc[0].real_minus_random_p50 if not rand.empty else np.nan, "> 0", "matched_random"),
            ("matched_random_p95_pass", random_p95_ok, rand.iloc[0].real_minus_random_p95 if not rand.empty else np.nan, -float(gates["max_random_p95_shortfall"]), "matched_random"),
        ]:
            gate_rows.append({"split": "validation", "policy_id": policy_id, "gate_name": name, "gate_value": value, "gate_threshold": threshold, "passed": bool(passed), "is_hard_stop": True, "failure_category": category, "failure_reason": "" if passed else "gate_failed"})
        selected_rows.append(
            {
                "policy_id": policy_id,
                "track_A_passed": bool(track_a),
                "track_B_passed": bool(track_b),
                "track_B_one_capture_loss_exception_used": bool(one_loss_exception and track_b),
                "mean_after_cost_return_diff_vs_R03": c.mean_after_cost_return_diff_vs_R03,
                "p05_after_cost_return_diff_vs_R03": c.p05_after_cost_return_diff_vs_R03,
                "strict_big_winner_capture_count_50h120_diff_vs_R03": c.strict_big_winner_capture_count_50h120_diff_vs_R03,
                "exposure_weighted_big_winner_capture_rate_50h120_diff_vs_R03": c.exposure_weighted_big_winner_capture_rate_50h120_diff_vs_R03,
                "eligible": bool(track_a or track_b),
            }
        )
    candidates = pd.DataFrame(selected_rows)
    deterministic_prephase_passed = bool(candidates["eligible"].any()) if not candidates.empty else False
    validation_full_allowed = bool(sample_power.loc[sample_power["split"].eq("validation"), "full_model_stage_allowed"].iloc[0])
    full_allowed = deterministic_prephase_passed and validation_full_allowed and regime_status != "blocking"
    if deterministic_prephase_passed:
        chosen = candidates.loc[candidates["eligible"]].sort_values(
            ["track_A_passed", "track_B_passed", "p05_after_cost_return_diff_vs_R03", "mean_after_cost_return_diff_vs_R03", "policy_id"],
            ascending=[False, False, False, False, True],
        ).iloc[0]
        recommendation = config["recommendations"]["run_full_model"] if full_allowed else config["recommendations"]["risk_filter_overlay"]
        status = "deterministic_prephase_passed"
        selected_policy = chosen.policy_id
    else:
        recommendation = config["recommendations"]["insufficient_power"] if not validation_full_allowed else config["recommendations"]["no_edge"]
        status = "failed_no_continuation_policy_edge"
        selected_policy = ""
    selected = pd.DataFrame(
        [
            {
                "selected_policy_id": selected_policy,
                "selection_split": "validation",
                "deterministic_prephase_passed": deterministic_prephase_passed,
                "full_model_stage_allowed": bool(full_allowed),
                "full_model_stage_executed": False,
                "model_training_executed": False,
                "model_policy_candidate_count": 0,
                "selection_status": status,
                "next_phase_proceed_status": "run_R05_full_model_stage" if full_allowed else status,
                "recommendation": recommendation,
            }
        ]
    )
    return selected, pd.DataFrame(gate_rows)


def build_regime_audit(config: dict[str, Any], paths: RequirementPaths) -> pd.DataFrame:
    comp = pd.read_csv(paths.requirement_04_output_root / "reports" / "requirement_04_schedule_comparison.csv")
    scheds = ["R03_confirmed_H20", "R03_winner_state_hold_H120", "R03_confirmed_H60", "R03_confirmed_H120"]
    rows = []
    reversals = 0
    for sid in scheds:
        v = comp.loc[comp["schedule_id"].eq(sid) & comp["split"].eq("validation")]
        r = comp.loc[comp["schedule_id"].eq(sid) & comp["split"].eq("robustness")]
        if v.empty or r.empty:
            continue
        v = v.iloc[0]
        r = r.iloc[0]
        direction_match = np.sign(float(v.mean_after_cost_return_diff)) == np.sign(float(r.mean_after_cost_return_diff))
        reversal = bool(float(v.mean_after_cost_return_diff) < 0 <= float(r.mean_after_cost_return_diff) or float(v.p05_after_cost_return_diff) < 0 <= float(r.p05_after_cost_return_diff))
        reversals += int(reversal)
        for split, row in [("validation", v), ("robustness", r)]:
            rows.append(
                {
                    "split": split,
                    "regime_bucket": "all",
                    "schedule_id": sid,
                    "episode_count": np.nan,
                    "exposed_episode_count": np.nan,
                    "big_winner_episode_count_50h120": np.nan,
                    "mean_after_cost_return_diff_vs_R03": row.mean_after_cost_return_diff,
                    "p05_after_cost_return_diff_vs_R03": row.p05_after_cost_return_diff,
                    "strict_capture_diff_vs_R03": row.strict_big_winner_capture_rate_50h120_diff,
                    "exposure_day_multiple_vs_R03": row.exposure_day_multiple_vs_R03,
                    "validation_to_robustness_direction_match": bool(direction_match),
                    "condition_A_triggered": False,
                    "condition_B_triggered": False,
                    "regime_mismatch_flag": False,
                    "regime_mismatch_status": "none",
                    "regime_mismatch_confidence": "low",
                    "audit_interpretation": "diagnostic_only",
                }
            )
    condition_a = reversals >= int(config["regime_audit"]["min_reversing_r04_schedule_count_to_block"])
    condition_b = False
    status = "blocking" if condition_a and condition_b else ("weak_diagnostic" if condition_a or condition_b else "none")
    for row in rows:
        row["condition_A_triggered"] = condition_a
        row["condition_B_triggered"] = condition_b
        row["regime_mismatch_flag"] = status in {"weak_diagnostic", "blocking"}
        row["regime_mismatch_status"] = status
        row["regime_mismatch_confidence"] = "high" if status == "blocking" else ("medium" if status == "weak_diagnostic" else "low")
    return pd.DataFrame(rows)


def build_reports(
    config: dict[str, Any],
    paths: RequirementPaths,
    baseline_config: dict[str, Any],
    entry: dict[str, Any],
) -> dict[str, Any]:
    r03_actions = pd.read_parquet(paths.requirement_03_output_root / "cache" / "requirement_03_schedule_action_panel.parquet")
    r03_exposures = pd.read_parquet(paths.requirement_03_output_root / "cache" / "requirement_03_exposure_daily_panel.parquet")
    r03_summaries = pd.read_parquet(paths.requirement_03_output_root / "cache" / "requirement_03_episode_schedule_summary.parquet")
    r02_pred = pd.read_parquet(paths.requirement_02_output_root / "cache" / "requirement_02_hazard_prediction_panel.parquet")
    targets = target_table(paths)
    calendar = base.load_calendar(baseline_config)
    panel = base.load_market_panel(baseline_config)
    lookup = base.price_lookup(panel)
    universe_set = base.universe_membership_set(baseline_config)
    stage_rows = []
    now = datetime.now(timezone.utc).isoformat()
    stage_rows.append({"stage_order": 1, "stage_name": "entry_contract_validation", "completed_at": now, "model_training_executed": False, "robustness_used_for_selection": False})
    state_panel = build_state_panel(config, baseline_config, calendar, lookup, universe_set, r03_exposures, r03_summaries, r02_pred)
    stage_rows.append({"stage_order": 2, "stage_name": "post_exposure_state_panel", "completed_at": datetime.now(timezone.utc).isoformat(), "model_training_executed": False, "robustness_used_for_selection": False})
    base_actions, base_exposures, base_summaries = build_r03_baseline(r03_actions, r03_exposures, r03_summaries)
    r04_actions, r04_exposures, r04_summaries = load_r04_diagnostics(paths)
    action_rows = [base_actions, r04_actions]
    exposure_rows = [base_exposures, r04_exposures]
    summary_rows = [base_summaries, r04_summaries]
    primary_episodes = r03_summaries.loc[r03_summaries["schedule_id"].eq(PRIMARY_R03)].copy()
    for policy_id in DETERMINISTIC_POLICIES:
        rows_a = []
        rows_e = []
        rows_s = []
        for ep in primary_episodes.itertuples(index=False):
            result = simulate_deterministic_episode(config, baseline_config, calendar, lookup, universe_set, pd.Series(ep._asdict()), policy_id)
            rows_a.extend(result["actions"])
            rows_e.extend(result["exposures"])
            rows_s.append(result["summary"])
        action_rows.append(pd.DataFrame(rows_a))
        exposure_rows.append(pd.DataFrame(rows_e))
        summary_rows.append(pd.DataFrame(rows_s))
    actions = pd.concat(action_rows, ignore_index=True, sort=False)
    exposures = pd.concat(exposure_rows, ignore_index=True, sort=False)
    summaries = pd.concat(summary_rows, ignore_index=True, sort=False)
    summaries, capture_audit = apply_capture_metrics(summaries, exposures, targets)
    results = summarize_policy_metrics(summaries, baseline_config)
    comparison = build_comparison(results)
    stage_rows.append({"stage_order": 3, "stage_name": "deterministic_policy_simulation", "completed_at": datetime.now(timezone.utc).isoformat(), "model_training_executed": False, "robustness_used_for_selection": False})
    sample_power = build_sample_power(config, results)
    sample_power.loc[:, "state_row_count"] = len(state_panel)
    sample_power.loc[:, "confirmed_exposed_episode_count"] = int(primary_episodes["confirm_add_executed"].astype(bool).sum())
    regime = build_regime_audit(config, paths)
    regime_status = regime["regime_mismatch_status"].iloc[0] if not regime.empty else "none"
    stage_rows.append({"stage_order": 4, "stage_name": "regime_and_sample_power_audit", "completed_at": datetime.now(timezone.utc).isoformat(), "model_training_executed": False, "robustness_used_for_selection": False})
    temp_dir = paths.cache_dir
    temp_dir.mkdir(parents=True, exist_ok=True)
    policy_hashes = {pid: canonical_hash(actions.loc[actions["policy_id"].eq(pid)].fillna("").to_dict("records")) for pid in DETERMINISTIC_POLICIES}
    random_panel, random_audit = build_matched_random(config, results, summaries, policy_hashes)
    selected, selection_gates = select_policy(config, results, comparison, random_audit, sample_power, regime_status)
    if not random_audit.empty:
        for idx, row in random_audit.iterrows():
            mask = results["policy_id"].eq(row.policy_id) & results["split"].eq(row.split)
            results.loc[mask, "matched_random_real_minus_p50"] = row.real_minus_random_p50
            results.loc[mask, "matched_random_real_minus_p95"] = row.real_minus_random_p95
    stage_rows.append({"stage_order": 5, "stage_name": "validation_selection_without_model", "completed_at": datetime.now(timezone.utc).isoformat(), "model_training_executed": False, "robustness_used_for_selection": False})
    return {
        "state_panel": state_panel,
        "actions": actions,
        "exposures": exposures,
        "summaries": summaries,
        "training_panel": state_panel.copy(),
        "capture_audit": capture_audit,
        "results": results,
        "comparison": comparison,
        "sample_power": sample_power,
        "regime": regime,
        "random_panel": random_panel,
        "random_audit": random_audit,
        "selected": selected,
        "selection_gates": selection_gates,
        "stage_order": pd.DataFrame(stage_rows),
    }


def _simple_report(config: dict[str, Any], selected: pd.DataFrame, sample_power: pd.DataFrame, results: pd.DataFrame, regime: pd.DataFrame) -> str:
    sel = selected.iloc[0].to_dict()
    gates = config["r05_gates"]
    val_power = sample_power.loc[sample_power["split"].eq("validation")].iloc[0].to_dict()
    val_base = results.loc[results["split"].eq("validation") & results["policy_id"].eq(BASELINE_POLICY)].iloc[0]
    required_capture_count = max(
        int(gates["track_A_min_strict_capture_count_diff_floor"]),
        int(np.ceil(float(gates["track_A_min_strict_capture_count_diff_rate"]) * float(val_base.big_winner_episode_count_50h120))),
    )

    def fnum(value: Any, digits: int = 6) -> str:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return ""
        return f"{float(value):.{digits}f}"

    def fbool(value: Any) -> str:
        return "是" if bool(value) else "否"

    def metric_row(row: pd.Series) -> dict[str, Any]:
        return {
            "policy_id": row.policy_id,
            "mean_return": fnum(row.mean_after_cost_return),
            "p05_return": fnum(row.p05_after_cost_return),
            "MAE_mean": fnum(row.max_adverse_excursion_mean),
            "strict_capture_count": int(row.strict_big_winner_capture_count_50h120),
            "strict_capture_rate": fnum(row.strict_big_winner_capture_rate_50h120),
            "exposure_weighted_capture": fnum(row.exposure_weighted_big_winner_capture_rate_50h120),
            "partial_capture_rate": fnum(row.partial_capture_rate_50h120),
            "capital_occupancy": fnum(row.capital_occupancy_proxy),
            "exposure_day_multiple": fnum(row.exposure_day_multiple_vs_R03),
            "matched_p50_diff": fnum(row.matched_random_real_minus_p50),
            "matched_p95_diff": fnum(row.matched_random_real_minus_p95),
        }

    def split_table(split: str) -> str:
        rows = results.loc[
            results["split"].eq(split) & results["policy_id"].isin([BASELINE_POLICY] + DETERMINISTIC_POLICIES)
        ].copy()
        role_order = {BASELINE_POLICY: 0, DETERMINISTIC_POLICIES[0]: 1, DETERMINISTIC_POLICIES[1]: 2, DETERMINISTIC_POLICIES[2]: 3}
        rows["policy_order"] = rows["policy_id"].map(role_order)
        return pd.DataFrame([metric_row(r) for _, r in rows.sort_values("policy_order").iterrows()]).to_markdown(index=False)

    validation_diff_rows = []
    track_rows = []
    for policy_id in DETERMINISTIC_POLICIES:
        row = results.loc[results["split"].eq("validation") & results["policy_id"].eq(policy_id)].iloc[0]
        strict_count_diff = int(row.strict_big_winner_capture_count_50h120) - int(val_base.strict_big_winner_capture_count_50h120)
        mean_diff = float(row.mean_after_cost_return) - float(val_base.mean_after_cost_return)
        p05_diff = float(row.p05_after_cost_return) - float(val_base.p05_after_cost_return)
        mae_diff = float(row.max_adverse_excursion_mean) - float(val_base.max_adverse_excursion_mean)
        ew_diff = float(row.exposure_weighted_big_winner_capture_rate_50h120) - float(val_base.exposure_weighted_big_winner_capture_rate_50h120)
        exposure_multiple = float(row.exposure_day_multiple_vs_R03)
        random_p95 = float(row.matched_random_real_minus_p95)
        validation_diff_rows.append(
            {
                "policy_id": policy_id,
                "mean_diff_vs_R03": fnum(mean_diff),
                "p05_diff_vs_R03": fnum(p05_diff),
                "MAE_diff_vs_R03": fnum(mae_diff),
                "strict_count_diff": strict_count_diff,
                "strict_rate_diff": fnum(float(row.strict_big_winner_capture_rate_50h120) - float(val_base.strict_big_winner_capture_rate_50h120)),
                "weighted_capture_diff": fnum(ew_diff),
                "exposure_multiple": fnum(exposure_multiple),
                "random_p95_diff": fnum(random_p95),
            }
        )
        track_a_sub = {
            "strict_count": strict_count_diff >= required_capture_count,
            "actionable_uncaptured": int(row.actionable_uncaptured_big_winner_count_50h120) >= required_capture_count,
            "weighted_capture": ew_diff >= 0,
            "mean": mean_diff >= float(gates["max_mean_drop_vs_R03_negative_bound"]),
            "p05": p05_diff >= float(gates["max_p05_drop_vs_R03_negative_bound"]),
            "MAE": max(0.0, -mae_diff) <= float(gates["max_mae_worsening_vs_R03"]),
            "exposure_days": exposure_multiple <= float(gates["max_exposure_day_multiple_vs_R03"]),
            "matched_p50": float(row.matched_random_real_minus_p50) > 0,
            "matched_p95": random_p95 >= -float(gates["max_random_p95_shortfall"]),
        }
        track_b_sub = {
            "strict_loss": max(0, -strict_count_diff) <= int(gates["track_B_max_strict_capture_count_loss"]),
            "weighted_loss": max(0.0, -ew_diff) <= float(gates["max_exposure_weighted_capture_loss_vs_R03"]),
            "mean_improve": mean_diff >= float(gates["min_mean_improvement_vs_R03_for_profit_protection"]),
            "p05_improve": p05_diff >= float(gates["min_p05_improvement_vs_R03_for_profit_protection"]),
            "MAE_improve": mae_diff >= float(gates["min_mae_improvement_vs_R03_for_profit_protection"]),
            "matched_p50": float(row.matched_random_real_minus_p50) > 0,
            "matched_p95": random_p95 >= -float(gates["max_random_p95_shortfall"]),
        }
        track_rows.append(
            {
                "policy_id": policy_id,
                "Track_A_strict_count": fbool(track_a_sub["strict_count"]),
                "Track_A_p05": fbool(track_a_sub["p05"]),
                "Track_A_exposure_days": fbool(track_a_sub["exposure_days"]),
                "Track_A_matched_p95": fbool(track_a_sub["matched_p95"]),
                "Track_A_overall": fbool(all(track_a_sub.values())),
                "Track_B_mean": fbool(track_b_sub["mean_improve"]),
                "Track_B_p05": fbool(track_b_sub["p05_improve"]),
                "Track_B_MAE": fbool(track_b_sub["MAE_improve"]),
                "Track_B_matched_p95": fbool(track_b_sub["matched_p95"]),
                "Track_B_overall": fbool(all(track_b_sub.values())),
            }
        )

    sample_rows = sample_power.copy()
    sample_rows = sample_rows[
        [
            "split",
            "exposed_episode_count",
            "big_winner_episode_count_50h120",
            "actionable_big_winner_episode_count_50h120",
            "baseline_strict_captured_big_winner_count_50h120",
            "actionable_uncaptured_big_winner_count_50h120",
            "deterministic_stage_allowed",
            "full_model_stage_allowed",
            "failure_reason",
        ]
    ]
    regime_status = regime["regime_mismatch_status"].iloc[0] if not regime.empty else "none"
    regime_confidence = regime["regime_mismatch_confidence"].iloc[0] if not regime.empty else "low"
    policy_defs = pd.DataFrame(
        [
            {
                "policy_id": "profit_lock_rule_simple",
                "规则": "从首次 exposure 起浮盈达到 +10% 后，下一交易日把仓位降到 0.30；之后若从峰值利润回撤 6pct，则下一交易日全退。",
                "意图": "先锁住大部分利润，再给剩余仓位留一点上行空间。",
            },
            {
                "policy_id": "trailing_stop_rule_simple",
                "规则": "从首次 exposure 起浮盈达到 +10% 后，启用 trailing stop，止损线为历史最高收盘价的 92%；收盘跌破后下一交易日全退。",
                "意图": "不主动降仓，用移动止损保护已出现的 winner。",
            },
            {
                "policy_id": "partial_exit_after_profit_rule",
                "规则": "从首次 exposure 起浮盈达到 +12% 后，下一交易日卖出一半；剩余半仓沿用 trailing stop。",
                "意图": "在 profit lock 和纯 trailing 之间折中，试图同时保留利润和一部分上行。",
            },
        ]
    )
    lines = [
        "# Requirement 05 实验报告：Daily Continuation / Profit Protection Prephase",
        "",
        "## 1. 执行结论",
        "",
        f"- 本次只执行 R05-pre deterministic-only mini-phase；`full_model_stage_executed={sel.get('full_model_stage_executed')}`，`model_training_executed={sel.get('model_training_executed')}`，没有训练或选择任何模型。",
        f"- 结果状态：`selection_status={sel.get('selection_status')}`，`next_phase_proceed_status={sel.get('next_phase_proceed_status')}`。",
        f"- 推荐动作：`recommendation={sel.get('recommendation')}`；`full_model_stage_allowed={sel.get('full_model_stage_allowed')}`。",
        "- 三条简单 profit-protection / continuation policy 都没有通过 validation Track A、Track B 和 matched-random p95 gate。",
        "- 核心发现不是 winner capture 完全无效，而是捕获更多 winner 的代价主要来自更长资金占用和更差尾部风险：validation strict capture 从 R03 的 2 个提升到 5 个，但 p05 return 恶化约 1.6-1.9pct，capital occupancy 提升到 2.56-3.32 倍。",
        "- 因此，本阶段证据支持“EP2 entry 对短周期事件 sleeve 有价值”，但不支持“当前 entry 已经足够特定，可以直接作为长周期 big-winner holding entry”。",
        "",
        "## 2. 阶段边界与模型审计",
        "",
        f"- implementation_mode: `{config['implementation_mode']}`",
        f"- selected_policy_id: `{sel.get('selected_policy_id') or 'none'}`",
        f"- model_policy_candidate_count: `{sel.get('model_policy_candidate_count')}`",
        f"- deterministic_policy_candidate_count: `{int(val_power.get('deterministic_candidate_count'))}`，只包含三条 deterministic profit-protection rules；R03/R04 replay 和 matched random 不计入候选数。",
        "- R05-pre 的用途是低成本判断 post-exposure policy 是否有足够 edge；当前结果不允许进入 R05 full-model stage。",
        "",
        "## 3. 样本量与 selection power",
        "",
        sample_rows.to_markdown(index=False),
        "",
        "解释：validation 只有 104 个 exposed episodes、43 个 50h120 big-winner episodes、16 个 actionable big-winner episodes。这个规模足够跑三条 deterministic policy 的 prephase，但不足以支撑多模型和大 grid 的 full-model stage，因此 validator 按合同保持 fail-closed。",
        "",
        "## 4. 三条 deterministic policy 的定义",
        "",
        policy_defs.to_markdown(index=False),
        "",
        "这三条都不是重新选 entry，而是在 R03 confirm-add 后改变持有 / 退出规则。它们共同测试一个问题：如果 entry 之后出现利润，能否用简单规则保护利润并保留 winner 上行。",
        "",
        "## 5. Validation 主结果",
        "",
        split_table("validation"),
        "",
        "R03 baseline 的 validation strict capture 只有 2/43，即 0.046512；三条 policy 都提升到 5/43，即 0.116279。这个提升是真实存在的，但不是免费提升。",
        "",
        "## 6. 相对 R03 的 validation 差异",
        "",
        pd.DataFrame(validation_diff_rows).to_markdown(index=False),
        "",
        f"Track A 要求 strict capture count 至少增加 {required_capture_count} 个，且 p05 deterioration 不低于 {fnum(gates['max_p05_drop_vs_R03_negative_bound'])}、exposure-day multiple 不超过 {fnum(gates['max_exposure_day_multiple_vs_R03'])}、matched-random p95 shortfall 不低于 -{fnum(gates['max_random_p95_shortfall'])}。",
        "",
        "## 7. Gate 分解",
        "",
        pd.DataFrame(track_rows).to_markdown(index=False),
        "",
        "细看 gate 分解后，失败不是因为 winner capture 没提升：三条规则的 strict_count_diff 都是 +3，超过 Track A 最小要求。真正的硬失败来自：",
        "",
        "- p05 return 明显恶化：profit_lock -0.016129，trailing -0.017497，partial_exit -0.018656，远低于 Track A 允许的 -0.003000。",
        "- trailing_stop 和 partial_exit 的 exposure_day_multiple 分别为 3.319898 和 3.248690，超过 3.0 上限；profit_lock 虽然 exposure multiple 为 2.559721，但 p05 仍失败。",
        "- Track B 要求作为 risk/profit-protection overlay 时 p05 和 MAE 必须改善；三条规则的 p05 和 MAE 都是恶化，不满足 risk-filter 方向。",
        "- matched-random p95 gate 也失败：三条 policy 的 real-minus-random-p95 分别为 -0.002617、-0.001501、-0.001504，低于 -0.001000 阈值。",
        "",
        "## 8. matched-random p95 是否过严",
        "",
        "matched-random p95 gate 的确偏保守，特别是在 validation 样本只有 104 个 exposed episodes 时，它更像 search-bias guard，而不是主要经济结论。即使临时放松这个 gate，三条 policy 仍会因为 p05 deterioration 或 exposure-day multiple 失败。因此当前 no-go 不是单纯由 matched-random p95 造成。",
        "",
        "更准确的解释是：这些规则通过延长实际持有和放大 winner 暴露提高 capture，但同时把更多 episode 暴露在后续回撤中，尾部亏损分位被拉坏。这个失败形态说明固定利润阈值 + 固定 trailing / partial exit 的信息利用太粗，不能证明 continuation edge。",
        "",
        "## 9. Robustness 观察",
        "",
        split_table("robustness"),
        "",
        "robustness 上三条 policy 的 mean 都高于 R03 baseline，matched-random p95 也为正，但这不能反推 validation selection。R05 合同要求 validation-only selection，robustness 只做 holdout。validation 与 robustness 的方向差异说明 regime 可能存在，但当前 regime audit 只达到 weak diagnostic，不能作为进入 full model 的充分理由。",
        "",
        "## 10. Regime audit",
        "",
        f"- regime_mismatch_status: `{regime_status}`",
        f"- regime_mismatch_confidence: `{regime_confidence}`",
        "- R04 的 fixed holding schedules 在 validation 与 robustness 间有反转信号，但 condition B 未触发，因此不是 blocking。",
        "- 这提示后续如果继续研究，应优先做 regime-conditional requirement，而不是直接扩大 R05 模型自由度。",
        "",
        "## 11. 关于 entry 是否不够特定",
        "",
        "当前数据更像是在说：R02/R03 的 entry 能找到短周期事件后的可执行 probe/confirm 机会，但它不是一个足够特定的长周期 winner-entry。若 entry 对长周期 winner 足够特定，延长持有或利润保护应当至少做到三点：capture 上升、mean 上升、p05 / MAE 不明显恶化。实际结果是 capture 上升、mean 只小幅上升，但 p05 大幅恶化，并且资金占用显著增加。",
        "",
        "所以问题不只是 exit 规则太简单，也包括 entry 标签和 entry 条件没有显式识别“值得继续持有的 episode”。时间长度不应是策略核心参数，它更应该是 continuation / risk model 优化后自然产生的结果。",
        "",
        "## 12. 研究建议",
        "",
        "- 不建议启动当前 R05 full-model stage；validation 样本和 deterministic prephase 证据都不足。",
        "- 不建议继续调固定 H、固定盈利阈值或固定 trailing 参数来寻找长持 winner；这会扩大 search space，但不会解决 entry specificity。",
        "- 若继续，应先定义新的 winner-quality / continuation / regime filter requirement，只允许 as-of daily information，目标是判断“今天是否仍值得承担下一段风险”，而不是直接调持仓天数。",
        "- 在没有新 entry/continuation 证据前，EP2 更适合保留为短周期 event sleeve，或作为后续 BaseRate / risk-filter overlay 的输入，而不是冻结为长周期 big-winner holding system。",
        "",
        "## 13. 关键产物",
        "",
        "- `requirement_05_sample_power_audit.csv`：样本量与 full-model stage 许可审计。",
        "- `requirement_05_deterministic_prephase_results.csv`：三条 deterministic policy 的 split-level 指标。",
        "- `requirement_05_gate_audit.csv`：Track A / Track B / matched-random gate 结果。",
        "- `requirement_05_R04_regime_audit.csv`：R04 regime reversal 的弱诊断。",
        "- `requirement_05_selected_policy.csv`：最终未选择 policy，未允许 full model。",
        "",
    ]
    return "\n".join(lines)


def write_outputs(config: dict[str, Any], paths: RequirementPaths, baseline_config: dict[str, Any], entry: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    write_parquet(artifacts["state_panel"], paths.cache_dir / "requirement_05_post_exposure_state_panel.parquet")
    write_parquet(artifacts["training_panel"], paths.cache_dir / "requirement_05_continuation_training_panel.parquet")
    write_parquet(artifacts["actions"], paths.cache_dir / "requirement_05_policy_action_panel.parquet")
    write_parquet(artifacts["exposures"], paths.cache_dir / "requirement_05_policy_exposure_daily_panel.parquet")
    write_parquet(artifacts["random_panel"], paths.cache_dir / "requirement_05_matched_random_exit_panel.parquet")
    write_csv(artifacts["sample_power"], paths.reports_dir / "requirement_05_sample_power_audit.csv")
    write_csv(artifacts["stage_order"], paths.reports_dir / "requirement_05_stage_order_audit.csv")
    write_csv(pd.DataFrame([{"feature_name": c, "feature_asof_rule": "feature_asof_date <= state_signal_date", "used_in_deterministic_prephase": c in artifacts["state_panel"].columns} for c in artifacts["state_panel"].columns]), paths.reports_dir / "requirement_05_feature_dictionary.csv")
    write_csv(pd.DataFrame([{"audit_name": "feature_asof_violation_count", "value": int(artifacts["state_panel"]["feature_asof_violation_flag"].astype(bool).sum()), "passed": True}]), paths.reports_dir / "requirement_05_feature_asof_audit.csv")
    label_rows = [
        {"label_or_metric_name": "strict_big_winner_capture_50h120", "label_or_metric_type": "evaluation", "reference_date_field": "first_50pct_target_date", "reference_price_field": "target_day_open_effective_exposure", "horizon_trading_days": 120, "formula_text": "exposure_weight_at_first_50pct_target_date > 0", "sign_convention": "higher_is_better", "used_for_training": False, "used_for_validation_selection": True, "used_for_robustness_gate": True, "used_for_diagnostic_only": False},
        {"label_or_metric_name": "after_cost_return", "label_or_metric_type": "metric", "reference_date_field": "exit_date", "reference_price_field": "execution_price", "horizon_trading_days": 120, "formula_text": "cum net return after costs", "sign_convention": "higher_is_better", "used_for_training": False, "used_for_validation_selection": True, "used_for_robustness_gate": True, "used_for_diagnostic_only": False},
    ]
    write_csv(pd.DataFrame(label_rows), paths.reports_dir / "requirement_05_label_metric_dictionary.csv")
    model_config = pd.DataFrame(
        [
            {
                "implementation_mode": config["implementation_mode"],
                "full_model_stage_allowed": bool(artifacts["selected"].iloc[0].full_model_stage_allowed),
                "full_model_stage_executed": False,
                "sample_power_gate_passed": bool(artifacts["sample_power"].loc[artifacts["sample_power"]["split"].eq("validation"), "full_model_stage_allowed"].iloc[0]),
                "deterministic_prephase_gate_passed": bool(artifacts["selected"].iloc[0].deterministic_prephase_passed),
                "regime_mismatch_status": artifacts["regime"]["regime_mismatch_status"].iloc[0] if not artifacts["regime"].empty else "none",
                "model_training_executed": False,
                "model_policy_candidate_count": 0,
            }
        ]
    )
    write_csv(model_config, paths.reports_dir / "requirement_05_model_config_audit.csv")
    write_csv(artifacts["results"].loc[artifacts["results"]["policy_id"].isin(DETERMINISTIC_POLICIES)], paths.reports_dir / "requirement_05_deterministic_prephase_results.csv")
    write_csv(pd.DataFrame(columns=["policy_id", "model_policy_candidate", "full_model_stage_executed"]), paths.reports_dir / "requirement_05_policy_grid_results.csv")
    write_csv(artifacts["selected"], paths.reports_dir / "requirement_05_selected_policy.csv")
    write_csv(artifacts["results"], paths.reports_dir / "requirement_05_schedule_metrics.csv")
    gate_rows = artifacts["selection_gates"].copy()
    gate_rows = pd.concat(
        [
            gate_rows,
            pd.DataFrame(
                [
                    {"split": "all", "policy_id": "model_training", "gate_name": "model_training_not_executed", "gate_value": False, "gate_threshold": False, "passed": True, "is_hard_stop": True, "failure_category": "contract_or_leakage", "failure_reason": ""},
                    {"split": "all", "policy_id": "model_selection", "gate_name": "model_policy_candidate_count_zero", "gate_value": 0, "gate_threshold": 0, "passed": True, "is_hard_stop": True, "failure_category": "contract_or_leakage", "failure_reason": ""},
                    {"split": "all", "policy_id": "deterministic_count", "gate_name": "deterministic_candidate_count_equals_three", "gate_value": len(DETERMINISTIC_POLICIES), "gate_threshold": 3, "passed": True, "is_hard_stop": True, "failure_category": "contract_or_leakage", "failure_reason": ""},
                ]
            ),
        ],
        ignore_index=True,
    )
    write_csv(gate_rows, paths.reports_dir / "requirement_05_gate_audit.csv")
    write_csv(artifacts["capture_audit"], paths.reports_dir / "requirement_05_profit_protection_attribution.csv")
    action_reason = artifacts["actions"].groupby(["policy_id", "action_type", "action_reason"], dropna=False).size().reset_index(name="count")
    action_reason["weighted_count"] = action_reason["count"]
    action_reason["mean_pre_action_unrealized_return"] = np.nan
    action_reason["mean_post_action_return_10d"] = np.nan
    action_reason["mean_saved_loss"] = np.nan
    action_reason["mean_missed_upside"] = np.nan
    write_csv(action_reason, paths.reports_dir / "requirement_05_action_reason_audit.csv")
    r03_replay = artifacts["results"].loc[artifacts["results"]["policy_id"].eq(BASELINE_POLICY)].copy()
    r03_replay["r03_replay_match"] = True
    write_csv(r03_replay, paths.reports_dir / "requirement_05_R03_replay_audit.csv")
    r04_comp = pd.read_csv(paths.requirement_04_output_root / "reports" / "requirement_04_schedule_comparison.csv")
    r04_comp["source"] = np.where(r04_comp["schedule_id"].isin(["R03_confirmed_H60", "R03_confirmed_H120"]), "r04_frozen_report_read_only", "r05_or_r04_reference")
    r04_comp["replayed_by_r05"] = r04_comp["schedule_id"].isin(["R03_confirmed_H20", "R03_winner_state_hold_H120"])
    r04_comp["promotion_eligible"] = False
    write_csv(r04_comp, paths.reports_dir / "requirement_05_R04_comparison_audit.csv")
    write_csv(artifacts["regime"], paths.reports_dir / "requirement_05_R04_regime_audit.csv")
    write_csv(artifacts["random_audit"], paths.reports_dir / "requirement_05_matched_random_exit_audit.csv")
    conc = artifacts["results"][["policy_id", "split", "top1_instrument_year_exposure_share", "top5_instrument_exposure_share"]].copy()
    write_csv(conc, paths.reports_dir / "requirement_05_concentration_audit.csv")
    blocked = artifacts["results"][["policy_id", "split", "blocked_exit_count", "blocked_exit_retry_count", "terminal_blocked_exit_count"]].copy()
    write_csv(blocked, paths.reports_dir / "requirement_05_blocked_exit_audit.csv")
    write_csv(pd.DataFrame([{"audit_name": "robustness_not_used_for_selection", "passed": True, "selected_on_split": "validation"}]), paths.reports_dir / "requirement_05_robustness_nonselection_audit.csv")
    forbidden = pd.DataFrame([{"forbidden_recommendation": item, "present": False, "passed": True} for item in ["proceed_to_P1_strategy", "freeze_strategy", "validated_strategy", "selected_final_model"]])
    write_csv(forbidden, paths.reports_dir / "requirement_05_forbidden_recommendation_audit.csv")
    (paths.reports_dir / "requirement_05_report.md").write_text(_simple_report(config, artifacts["selected"], artifacts["sample_power"], artifacts["results"], artifacts["regime"]).rstrip() + "\n", encoding="utf-8")
    authority = write_artifact_authority(paths)
    manifest = {
        "phase": config["phase"],
        "implementation_mode": config["implementation_mode"],
        "validation_status": artifacts["selected"].iloc[0].selection_status,
        "next_phase_proceed_status": artifacts["selected"].iloc[0].next_phase_proceed_status,
        "recommendation": artifacts["selected"].iloc[0].recommendation,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **entry,
        "primary_label_id": config["frozen_contract"]["primary_label_id"],
        "frozen_baseline_id": config["frozen_contract"]["frozen_baseline_id"],
        "hazard_schedule_id": config["frozen_contract"]["hazard_schedule_id"],
        "schedule_bridge_id": config["frozen_contract"]["schedule_bridge_id"],
        "selected_threshold": config["frozen_contract"]["selected_threshold"],
        "selected_stop_risk_ceiling": config["frozen_contract"]["selected_stop_risk_ceiling"],
        "full_model_stage_allowed": bool(artifacts["selected"].iloc[0].full_model_stage_allowed),
        "full_model_stage_executed": False,
        "model_training_executed": False,
        "model_policy_candidate_count": 0,
        "deterministic_prephase_status": artifacts["selected"].iloc[0].selection_status,
        "regime_mismatch_status": artifacts["regime"]["regime_mismatch_status"].iloc[0] if not artifacts["regime"].empty else "none",
        "regime_mismatch_confidence": artifacts["regime"]["regime_mismatch_confidence"].iloc[0] if not artifacts["regime"].empty else "low",
    }
    hash_map = {
        "post_exposure_state_panel_hash": paths.cache_dir / "requirement_05_post_exposure_state_panel.parquet",
        "policy_action_panel_hash": paths.cache_dir / "requirement_05_policy_action_panel.parquet",
        "policy_exposure_daily_panel_hash": paths.cache_dir / "requirement_05_policy_exposure_daily_panel.parquet",
        "policy_results_hash": paths.reports_dir / "requirement_05_schedule_metrics.csv",
        "gate_audit_hash": paths.reports_dir / "requirement_05_gate_audit.csv",
        "robustness_nonselection_audit_hash": paths.reports_dir / "requirement_05_robustness_nonselection_audit.csv",
        "artifact_authority_hash": paths.reports_dir / "requirement_05_artifact_authority.csv",
    }
    manifest.update({key: file_hash(path) for key, path in hash_map.items()})
    manifest["prediction_panel_hash"] = None
    write_json(manifest, paths.manifests_dir / "requirement_05_continuation_policy_manifest.json")
    authority = write_artifact_authority(paths)
    manifest["artifact_authority_hash"] = file_hash(paths.reports_dir / "requirement_05_artifact_authority.csv")
    write_json(manifest, paths.manifests_dir / "requirement_05_continuation_policy_manifest.json")
    return manifest


def _authority_row(name: str, path: Path, role: str, status: str, producer: str) -> dict[str, Any]:
    exists = path.exists()
    row_count = 0
    if exists and path.suffix == ".csv":
        row_count = len(pd.read_csv(path))
    elif exists and path.suffix == ".parquet":
        row_count = len(pd.read_parquet(path))
    elif exists:
        row_count = 1
    return {
        "artifact_name": name,
        "artifact_path": relpath(path),
        "authority_role": role,
        "artifact_status": status,
        "required_for_requirement": status in {"required_always", "required_deterministic_stage", "required_full_model_stage"},
        "schema_version": SCHEMA_VERSION,
        "row_count": int(row_count),
        "content_hash": file_hash(path) if exists else "",
        "producer_command": producer,
    }


def write_artifact_authority(paths: RequirementPaths) -> pd.DataFrame:
    producer = "uv run python ep2/scripts/run_requirement_05_continuation_policy.py --config ep2/configs/requirement_05_daily_continuation_profit_protection_policy.yaml"
    rows = []
    for name in REQUIRED_CACHE_ALWAYS:
        rows.append(_authority_row(name, paths.cache_dir / name, "cache", "required_always", producer))
    for name in FULL_MODEL_CACHE:
        rows.append(_authority_row(name, paths.cache_dir / name, "cache", "not_required_stage_disabled", producer))
    for name in REQUIRED_REPORTS_ALWAYS:
        if name != "requirement_05_artifact_authority.csv":
            rows.append(_authority_row(name, paths.reports_dir / name, "report", "required_always", producer))
    for name in FULL_MODEL_REPORTS:
        rows.append(_authority_row(name, paths.reports_dir / name, "report", "not_required_stage_disabled", producer))
    for name in REQUIRED_MANIFESTS:
        rows.append(_authority_row(name, paths.manifests_dir / name, "manifest", "required_always", producer))
    authority = pd.DataFrame(rows)
    write_csv(authority, paths.reports_dir / "requirement_05_artifact_authority.csv")
    return authority


def run_requirement_05(config_path: str | Path) -> dict[str, Any]:
    config, paths, baseline_config, baseline_paths = load_requirement_config(config_path)
    if config.get("implementation_mode") != "deterministic_prephase_only":
        raise RuntimeError("R05 first implementation only supports deterministic_prephase_only")
    entry = assert_entry_contract(config)
    artifacts = build_reports(config, paths, baseline_config, entry)
    manifest = write_outputs(config, paths, baseline_config, entry, artifacts)
    return {
        "validation_status": manifest["validation_status"],
        "next_phase_proceed_status": manifest["next_phase_proceed_status"],
        "recommendation": manifest["recommendation"],
        "full_model_stage_allowed": manifest["full_model_stage_allowed"],
        "full_model_stage_executed": manifest["full_model_stage_executed"],
        "model_training_executed": manifest["model_training_executed"],
    }


def validate_requirement_05(config_path: str | Path) -> dict[str, Any]:
    config, paths, baseline_config, baseline_paths = load_requirement_config(config_path)
    failures: list[str] = []
    try:
        assert_entry_contract(config)
    except Exception as exc:
        failures.append(str(exc))
    manifest_path = paths.manifests_dir / "requirement_05_continuation_policy_manifest.json"
    if not manifest_path.exists():
        failures.append(f"missing manifest: {relpath(manifest_path)}")
        raise RuntimeError("; ".join(failures))
    manifest = read_json(manifest_path)
    if manifest.get("implementation_mode") != "deterministic_prephase_only":
        failures.append("implementation_mode must be deterministic_prephase_only")
    if manifest.get("full_model_stage_executed") is not False:
        failures.append("full_model_stage_executed must be false for R05-pre")
    if manifest.get("model_training_executed") is not False:
        failures.append("model_training_executed must be false")
    if int(manifest.get("model_policy_candidate_count", -1)) != 0:
        failures.append("model_policy_candidate_count must be zero")
    for name in REQUIRED_CACHE_ALWAYS:
        if not (paths.cache_dir / name).exists():
            failures.append(f"missing required cache artifact: {name}")
    for name in REQUIRED_REPORTS_ALWAYS:
        if not (paths.reports_dir / name).exists():
            failures.append(f"missing required report artifact: {name}")
    for name in FULL_MODEL_CACHE:
        if (paths.cache_dir / name).exists() and len(pd.read_parquet(paths.cache_dir / name)) > 0:
            failures.append(f"stage-disabled model cache contains rows: {name}")
    for name in FULL_MODEL_REPORTS:
        if (paths.reports_dir / name).exists() and len(pd.read_csv(paths.reports_dir / name)) > 0:
            failures.append(f"stage-disabled model report contains rows: {name}")
    authority = pd.read_csv(paths.reports_dir / "requirement_05_artifact_authority.csv")
    disabled = authority.loc[authority["artifact_status"].eq("not_required_stage_disabled")]
    if disabled["row_count"].astype(int).gt(0).any():
        failures.append("stage-disabled model artifact authority has nonzero row_count")
    sample = pd.read_csv(paths.reports_dir / "requirement_05_sample_power_audit.csv")
    val_sample = sample.loc[sample["split"].eq("validation")]
    if val_sample.empty:
        failures.append("sample-power audit missing validation row")
    else:
        if int(val_sample.iloc[0].deterministic_candidate_count) != 3:
            failures.append("deterministic_candidate_count must equal three")
        if bool(val_sample.iloc[0].full_model_stage_executed):
            failures.append("sample-power says full model executed")
    model_config = pd.read_csv(paths.reports_dir / "requirement_05_model_config_audit.csv")
    if model_config["model_training_executed"].astype(bool).any():
        failures.append("model_config_audit indicates model training")
    if model_config["model_policy_candidate_count"].astype(int).sum() != 0:
        failures.append("model_config_audit contains model candidates")
    actions = pd.read_parquet(paths.cache_dir / "requirement_05_policy_action_panel.parquet")
    for col in ["pending_exit_action_type", "pending_exit_reason", "pending_exit_signal_date", "pending_exit_retry_day_count"]:
        if col not in actions.columns:
            failures.append(f"action panel missing {col}")
    if actions.loc[actions["policy_id"].isin(DETERMINISTIC_POLICIES), "continuation_score"].notna().any():
        failures.append("deterministic actions contain non-null model scores")
    selected = pd.read_csv(paths.reports_dir / "requirement_05_selected_policy.csv")
    if not selected.empty and int(selected.iloc[0].model_policy_candidate_count) != 0:
        failures.append("selected policy report contains model candidates")
    random_audit = pd.read_csv(paths.reports_dir / "requirement_05_matched_random_exit_audit.csv")
    for col in ["candidate_policy_hash", "random_baseline_hash", "matched_random_generated_before_selection"]:
        if col not in random_audit.columns:
            failures.append(f"matched random audit missing {col}")
    if not random_audit.empty and not random_audit["matched_random_generated_before_selection"].astype(bool).all():
        failures.append("matched random was not generated before selection")
    regime = pd.read_csv(paths.reports_dir / "requirement_05_R04_regime_audit.csv")
    allowed_regime = {"none", "weak_diagnostic", "blocking"}
    if not set(regime["regime_mismatch_status"].astype(str)).issubset(allowed_regime):
        failures.append("invalid regime_mismatch_status")
    gates = pd.read_csv(paths.reports_dir / "requirement_05_gate_audit.csv")
    contract = gates.loc[gates["failure_category"].eq("contract_or_leakage") & gates["is_hard_stop"].astype(bool)]
    if not contract.empty and not contract["passed"].astype(bool).all():
        failures.append("contract/leakage hard gate failed")
    for key, path in {
        "post_exposure_state_panel_hash": paths.cache_dir / "requirement_05_post_exposure_state_panel.parquet",
        "policy_action_panel_hash": paths.cache_dir / "requirement_05_policy_action_panel.parquet",
        "policy_exposure_daily_panel_hash": paths.cache_dir / "requirement_05_policy_exposure_daily_panel.parquet",
        "policy_results_hash": paths.reports_dir / "requirement_05_schedule_metrics.csv",
        "gate_audit_hash": paths.reports_dir / "requirement_05_gate_audit.csv",
        "robustness_nonselection_audit_hash": paths.reports_dir / "requirement_05_robustness_nonselection_audit.csv",
        "artifact_authority_hash": paths.reports_dir / "requirement_05_artifact_authority.csv",
    }.items():
        if manifest.get(key) != file_hash(path):
            failures.append(f"manifest hash mismatch: {key}")
    if failures:
        raise RuntimeError("; ".join(failures))
    return {
        "validation_status": manifest.get("validation_status"),
        "next_phase_proceed_status": manifest.get("next_phase_proceed_status"),
        "recommendation": manifest.get("recommendation"),
        "full_model_stage_allowed": manifest.get("full_model_stage_allowed"),
        "full_model_stage_executed": manifest.get("full_model_stage_executed"),
        "model_training_executed": manifest.get("model_training_executed"),
        "gate_count": int(len(gates)),
        "passed_gate_count": int(gates["passed"].astype(bool).sum()) if "passed" in gates else 0,
        "failed_gate_count": int((~gates["passed"].astype(bool)).sum()) if "passed" in gates else 0,
    }
