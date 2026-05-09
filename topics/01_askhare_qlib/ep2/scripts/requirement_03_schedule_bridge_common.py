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


SCHEMA_VERSION = "requirement_03_schedule_bridge_v1"
PRIMARY_SCHEDULE_ID = "hazard_probe_confirm_add_fast_fail"
R02_REPLAY_SCHEDULE_ID = "hazard_probe_with_simple_stop_replay"
NO_FAST_FAIL_SCHEDULE_ID = "hazard_probe_confirm_add_no_fast_fail"
R02_HAZARD_SCHEDULE_ID = "hazard_probe_with_simple_stop"

REQUIRED_CACHE = [
    "requirement_03_schedule_action_panel.parquet",
    "requirement_03_exposure_daily_panel.parquet",
    "requirement_03_episode_schedule_summary.parquet",
]
REQUIRED_REPORTS = [
    "requirement_03_schedule_results.csv",
    "requirement_03_schedule_comparison.csv",
    "requirement_03_confirm_add_audit.csv",
    "requirement_03_gate_audit.csv",
    "requirement_03_baserate_launch_overlap.csv",
    "requirement_03_baserate_score_overlap.csv",
    "requirement_03_baserate_uncovered_opportunity.csv",
    "requirement_03_baserate_coverage_gate.csv",
    "requirement_03_baserate_leakage_audit.csv",
    "requirement_03_stage_order_audit.csv",
    "requirement_03_artifact_authority.csv",
]
REQUIRED_MANIFESTS = ["requirement_03_schedule_bridge_manifest.json"]


@dataclass(frozen=True)
class RequirementPaths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    reports_dir: Path
    manifests_dir: Path
    baseline_config_path: Path
    baseline_output_root: Path
    requirement_02_output_root: Path
    base_rate_root: Path


class StageAudit:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(
        self,
        stage_name: str,
        stage_order: int,
        input_artifact_name: str = "",
        input_artifact_hash: str = "",
        output_artifact_name: str = "",
        output_artifact_hash: str = "",
        base_rate_rows_available: bool = False,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.rows.append(
            {
                "stage_name": stage_name,
                "stage_order": int(stage_order),
                "started_at": now,
                "completed_at": now,
                "input_artifact_name": input_artifact_name,
                "input_artifact_hash": input_artifact_hash,
                "output_artifact_name": output_artifact_name,
                "output_artifact_hash": output_artifact_hash,
                "base_rate_rows_available": bool(base_rate_rows_available),
            }
        )

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    return base.relpath(path)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def load_requirement_config(config_path: str | Path) -> tuple[dict[str, Any], RequirementPaths, dict[str, Any], base.Paths]:
    cfg_path = topic_path(config_path)
    with cfg_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    output_root = topic_path(config["output_root"])
    baseline_config_path = topic_path(config["baseline"]["config_path"])
    with baseline_config_path.open("r", encoding="utf-8") as file:
        baseline_config = yaml.safe_load(file) or {}
    baseline_output_root = topic_path(config["baseline"]["output_root"])
    paths = RequirementPaths(
        config_path=cfg_path,
        output_root=output_root,
        cache_dir=output_root / "cache",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
        baseline_config_path=baseline_config_path,
        baseline_output_root=baseline_output_root,
        requirement_02_output_root=topic_path(config["inputs"]["requirement_02_output_root"]),
        base_rate_root=topic_path(config["baserate_bridge"]["base_rate_root"]),
    )
    baseline_paths = base.Paths(
        config_path=baseline_config_path,
        output_root=baseline_output_root,
        cache_dir=baseline_output_root / "cache",
        reports_dir=baseline_output_root / "reports",
        manifests_dir=baseline_output_root / "manifests",
    )
    for directory in [paths.cache_dir, paths.reports_dir, paths.manifests_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths, baseline_config, baseline_paths


def _date_str(value: Any) -> str:
    if pd.isna(value) or str(value) in {"", "NaT", "nan", "None"}:
        return ""
    return pd.Timestamp(value).date().isoformat()


def _as_date_or_nat(value: Any) -> pd.Timestamp | pd.NaT:
    if pd.isna(value) or str(value) in {"", "NaT", "nan", "None"}:
        return pd.NaT
    return pd.Timestamp(value).normalize()


def _same_float(a: Any, b: Any, tol: float = 1e-12) -> bool:
    return abs(float(a) - float(b)) <= tol


def assert_requirement_02_entry(config: dict[str, Any]) -> dict[str, Any]:
    frozen = config["frozen_contract"]
    manifest_path = topic_path(frozen["requirement_02_manifest"])
    gate_path = topic_path(frozen["requirement_02_gate_audit"])
    if not manifest_path.exists():
        raise RuntimeError(f"missing Requirement 02 manifest: {relpath(manifest_path)}")
    if not gate_path.exists():
        raise RuntimeError(f"missing Requirement 02 gate audit: {relpath(gate_path)}")
    manifest = read_json(manifest_path)
    checks = {
        "phase": "requirement_02_hazard_timing_model",
        "validation_status": frozen["expected_requirement_02_status"],
        "requirement_03_proceed_status": frozen["expected_requirement_02_status"],
        "primary_label_id": frozen["primary_label_id"],
        "frozen_baseline_id": frozen["frozen_baseline_id"],
    }
    failures = [f"Requirement 02 {key} expected {expected}, observed {manifest.get(key)}" for key, expected in checks.items() if manifest.get(key) != expected]
    if not _same_float(manifest.get("selected_threshold"), frozen["selected_threshold"]):
        failures.append("Requirement 02 selected_threshold mismatch")
    if not _same_float(manifest.get("selected_stop_risk_ceiling"), frozen["selected_stop_risk_ceiling"]):
        failures.append("Requirement 02 selected_stop_risk_ceiling mismatch")
    gates = pd.read_csv(gate_path)
    gate_count = int(len(gates))
    passed_count = int(gates["passed"].astype(bool).sum()) if "passed" in gates else 0
    failed_count = gate_count - passed_count
    if gate_count != int(frozen["requirement_02_expected_gate_count"]):
        failures.append(f"Requirement 02 gate_count expected {frozen['requirement_02_expected_gate_count']}, observed {gate_count}")
    if passed_count != int(frozen["requirement_02_expected_passed_gate_count"]):
        failures.append(f"Requirement 02 passed_gate_count expected {frozen['requirement_02_expected_passed_gate_count']}, observed {passed_count}")
    if failed_count != int(frozen["requirement_02_expected_failed_gate_count"]):
        failures.append(f"Requirement 02 failed_gate_count expected {frozen['requirement_02_expected_failed_gate_count']}, observed {failed_count}")
    if failures:
        raise RuntimeError("; ".join(failures))
    return {
        "manifest": manifest,
        "manifest_hash": file_hash(manifest_path),
        "gate_audit_hash": file_hash(gate_path),
        "gate_count": gate_count,
        "passed_gate_count": passed_count,
        "failed_gate_count": failed_count,
    }


def _positive_pnl_concentration(df: pd.DataFrame) -> tuple[int, float, float]:
    if df.empty:
        return 0, 0.0, 0.0
    tmp = df.copy()
    tmp["first_exposure_date"] = pd.to_datetime(tmp["first_exposure_date"], errors="coerce")
    tmp["year"] = tmp["first_exposure_date"].dt.year
    positive = tmp.loc[tmp["after_cost_return"].astype(float) > 0]
    if positive.empty:
        return 0, 0.0, 0.0
    by_year = positive.groupby("year", dropna=True)["after_cost_return"].sum()
    total = float(by_year.sum())
    year_share = float(by_year.max() / total) if total > 0 else 0.0
    keys = positive["instrument"].astype(str) + "_" + positive["year"].fillna(0).astype(int).astype(str)
    by_inst_year = positive.groupby(keys)["after_cost_return"].sum()
    inst_share = float(by_inst_year.max() / total) if total > 0 and not by_inst_year.empty else 0.0
    return int(by_year.shape[0]), year_share, inst_share


def _instrument_concentration(df: pd.DataFrame) -> tuple[float, float]:
    if df.empty:
        return 0.0, 0.0
    dates = pd.to_datetime(df["first_exposure_date"], errors="coerce")
    keys = df["instrument"].astype(str) + "_" + dates.dt.year.fillna(0).astype(int).astype(str)
    shares = keys.value_counts(normalize=True)
    return float(shares.iloc[0]) if not shares.empty else 0.0, float(shares.head(5).sum()) if not shares.empty else 0.0


def _empty_episode_summary(schedule_id: str, split: str, episode: Any, selected: pd.Series | None = None, no_probe_reason: str = "no_requirement_02_probe") -> dict[str, Any]:
    return {
        "schedule_id": schedule_id,
        "split": split,
        "launch_episode_id": str(episode.launch_episode_id),
        "instrument": str(episode.instrument).upper(),
        "launch_effective_date": _date_str(episode.launch_effective_date),
        "selected_probe_signal_date": _date_str(selected["selected_probe_signal_date"]) if selected is not None else "",
        "selected_probe_execution_date": _date_str(selected["selected_probe_execution_date"]) if selected is not None else "",
        "confirm_add_signal_date": "",
        "confirm_add_execution_date": "",
        "probe_executed": False,
        "confirm_add_executed": False,
        "fast_fail_exit": False,
        "natural_exit": False,
        "had_exposure": False,
        "no_probe": True,
        "confirm_added": False,
        "fast_failed": False,
        "natural_exited": False,
        "after_cost_return": 0.0,
        "missed_gain_to_exposure": np.nan,
        "turnover": 0.0,
        "first_exposure_date": "",
        "exit_date": "",
        "selection_status": "no_probe",
        "no_probe_reason": no_probe_reason,
        "no_confirm_add_reason": "no_probe",
        "first_exposure_price": np.nan,
    }


def _select_confirm_add_candidate(
    config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    candidates: pd.DataFrame,
    selected: pd.Series,
) -> pd.Series | None:
    if candidates.empty:
        return None
    sched = config["schedule_bridge"]
    threshold = float(config["frozen_contract"]["selected_threshold"])
    stop_ceiling = float(config["frozen_contract"]["selected_stop_risk_ceiling"])
    probe_exec = _as_date_or_nat(selected["selected_probe_execution_date"])
    launch_date = _as_date_or_nat(candidates["launch_effective_date"].iloc[0])
    if pd.isna(probe_exec) or pd.isna(launch_date):
        return None
    start = base.add_trading_days(calendar, probe_exec, int(sched["confirm_add_search_start_offset_trading_days"]))
    probe_end = base.add_trading_days(calendar, probe_exec, int(sched["confirm_add_search_end_offset_trading_days"]))
    launch_end = base.add_trading_days(calendar, launch_date, int(sched["max_confirm_add_days_from_launch_execution"]))
    if pd.isna(start) or pd.isna(probe_end) or pd.isna(launch_end):
        return None
    end = min(probe_end, launch_end)
    group = candidates.copy()
    group["_exec"] = pd.to_datetime(group["probe_execution_date"]).dt.normalize()
    valid = group.loc[
        group["_exec"].ge(start)
        & group["_exec"].le(end)
        & group["is_valid_probe_candidate"].astype(bool)
        & group["score_probe_day"].astype(float).ge(threshold)
        & group["P_stop_first"].astype(float).le(stop_ceiling)
        & (~group["pre_probe_fast_fail_from_launch_reference"].astype(bool))
        & group["missed_gain_to_probe"].astype(float).le(float(sched["max_missed_gain_to_confirm"]))
        & group["is_buy_executable_next_open"].astype(bool)
    ].sort_values(["probe_execution_date", "probe_signal_date"])
    if valid.empty:
        return None
    return valid.iloc[0]


def _simulate_episode(
    config: dict[str, Any],
    baseline_config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    universe_set: set[tuple[str, pd.Timestamp]],
    episode: Any,
    selected: pd.Series | None,
    candidate_group: pd.DataFrame,
    split: str,
    schedule_id: str,
    fast_fail_enabled: bool,
    confirm_add_enabled: bool,
) -> dict[str, Any]:
    instrument = str(episode.instrument).upper()
    if selected is None or _date_str(selected.get("selected_probe_execution_date", "")) == "":
        return {"actions": [], "exposures": [], "summary": _empty_episode_summary(schedule_id, split, episode, selected)}

    sched = config["schedule_bridge"]
    probe_signal = _as_date_or_nat(selected["selected_probe_signal_date"])
    probe_exec = _as_date_or_nat(selected["selected_probe_execution_date"])
    confirm = _select_confirm_add_candidate(config, calendar, candidate_group, selected) if confirm_add_enabled else None
    confirm_exec = _as_date_or_nat(confirm["probe_execution_date"]) if confirm is not None else pd.NaT
    confirm_signal = _as_date_or_nat(confirm["probe_signal_date"]) if confirm is not None else pd.NaT
    h_days = int(sched["primary_H"])
    fast_fail_drawdown = float(sched["fast_fail_drawdown"])
    rates = base.cost_rates(baseline_config)
    limit_pct = float(baseline_config["execution"]["limit_inference_pct"]["mainboard_default"])
    exit_retry_until = int(baseline_config["schedule_defaults"]["blocked_exit_retry"]["max_retry_trading_days"])
    sim_end = base.add_trading_days(calendar, probe_exec, h_days + exit_retry_until + int(sched["confirm_add_search_end_offset_trading_days"]) + 2)
    if pd.isna(sim_end):
        sim_end = calendar[-1]
    sim_dates = calendar[(calendar >= probe_exec) & (calendar <= sim_end)]

    actions: list[dict[str, Any]] = []
    exposures: list[dict[str, Any]] = []
    state = "no_exposure"
    target_weight = 0.0
    actual_weight = 0.0
    first_exposure_date = pd.NaT
    first_exposure_price = np.nan
    exited_date = pd.NaT
    natural_exit_date = pd.NaT
    fast_failed = False
    natural_exited = False
    probe_executed = False
    confirm_executed = False
    total_order_notional = 0.0
    total_cost = 0.0
    missed_gain_to_exposure = np.nan
    cum_gross = 0.0
    cum_net = 0.0
    prev_close = np.nan
    pending_exit: dict[str, Any] | None = None
    terminal_blocked = False

    for date in sim_dates:
        info = lookup.get((instrument, pd.Timestamp(date)), {})
        open_price = float(info.get("open", np.nan))
        close_price = float(info.get("close", np.nan))
        low_price = float(info.get("low", np.nan))
        day_cost = 0.0
        day_gross = 0.0
        if actual_weight > 0 and np.isfinite(close_price):
            reference = prev_close if np.isfinite(prev_close) else (open_price if np.isfinite(open_price) else np.nan)
            if np.isfinite(reference) and reference > 0:
                day_gross = actual_weight * (close_price / reference - 1.0)
        signal_date = base.prev_trading_day(calendar, date)
        scheduled: list[dict[str, Any]] = []
        if pending_exit is not None:
            scheduled.append({"action_type": pending_exit["action_type"], "target_weight_after": 0.0, "is_exit": True, "retry": True})
        if actual_weight > 0 and pending_exit is None:
            if fast_fail_enabled and np.isfinite(low_price) and np.isfinite(first_exposure_price) and low_price / first_exposure_price - 1.0 <= -fast_fail_drawdown:
                scheduled.append({"action_type": "fast_fail_exit", "target_weight_after": 0.0, "is_exit": True, "retry": False})
            elif not pd.isna(natural_exit_date) and date >= natural_exit_date:
                scheduled.append({"action_type": "natural_exit", "target_weight_after": 0.0, "is_exit": True, "retry": False})
        if date == probe_exec:
            scheduled.append({"action_type": "probe_entry", "target_weight_after": float(sched["probe_weight"]), "is_exit": False, "retry": False})
        if confirm_add_enabled and not pd.isna(confirm_exec) and date == confirm_exec and actual_weight > 0 and not fast_failed:
            scheduled.append({"action_type": "confirm_add", "target_weight_after": float(sched["full_weight_after_confirm"]), "is_exit": False, "retry": False})

        for action in sorted(scheduled, key=lambda item: base._action_priority(item["action_type"])):
            before_state = state
            before_weight = target_weight
            action_type = action["action_type"]
            desired_weight = float(action["target_weight_after"])
            is_exit = bool(action["is_exit"])
            if is_exit and actual_weight <= 0:
                continue
            if not is_exit and desired_weight <= actual_weight:
                continue
            status = base.execution_status(lookup, universe_set, instrument, signal_date, date, limit_pct)
            blocked_reason = status["blocked_sell_reason"] if is_exit else status["blocked_buy_reason"]
            executable = not bool(blocked_reason)
            order_notional = abs(actual_weight - desired_weight)
            commission = stamp = slippage = action_cost = 0.0
            terminal_policy = ""
            exit_status = "not_exit"
            if executable:
                if is_exit:
                    commission = order_notional * rates["commission_sell"]
                    stamp = order_notional * rates["stamp_tax_sell"]
                    slippage = order_notional * rates["slippage_sell"]
                    actual_weight = 0.0
                    target_weight = 0.0
                    state = "exited"
                    exited_date = pd.Timestamp(date)
                    pending_exit = None
                    natural_exited = action_type == "natural_exit"
                    fast_failed = action_type == "fast_fail_exit"
                    exit_status = "retry_exit" if action.get("retry") else "normal_exit"
                else:
                    commission = order_notional * rates["commission_buy"]
                    slippage = order_notional * rates["slippage_buy"]
                    target_weight = desired_weight
                    actual_weight = desired_weight
                    if pd.isna(first_exposure_date):
                        first_exposure_date = pd.Timestamp(date)
                        first_exposure_price = float(status["execution_price_reference"])
                        launch_open = float(lookup.get((instrument, base.as_date(episode.launch_effective_date)), {}).get("open", np.nan))
                        missed_gain_to_exposure = first_exposure_price / launch_open - 1.0 if np.isfinite(first_exposure_price) and np.isfinite(launch_open) and launch_open > 0 else np.nan
                        natural_exit_date = base.add_trading_days(calendar, date, h_days)
                    state = "full_exposure" if actual_weight >= 1.0 else "partial_exposure"
                    probe_executed = probe_executed or action_type == "probe_entry"
                    confirm_executed = confirm_executed or action_type == "confirm_add"
                action_cost = commission + stamp + slippage
                day_cost += action_cost
                total_cost += action_cost
                total_order_notional += order_notional
            else:
                if is_exit:
                    retry_count = pending_exit["retry_count"] + 1 if pending_exit else 1
                    if retry_count > exit_retry_until:
                        terminal_blocked = True
                        terminal_policy = baseline_config["schedule_defaults"]["blocked_exit_retry"]["terminal_price_policy"]
                        state = "exited"
                        target_weight = 0.0
                        actual_weight = 0.0
                        exited_date = pd.Timestamp(date)
                        pending_exit = None
                        exit_status = "terminal_blocked_exit"
                    else:
                        pending_exit = {"action_type": action_type, "retry_count": retry_count}
                else:
                    action_type = "blocked_action"
            actions.append(
                {
                    "schedule_id": schedule_id,
                    "launch_episode_id": str(episode.launch_episode_id),
                    "instrument": instrument,
                    "signal_date": _date_str(signal_date),
                    "decision_date": _date_str(signal_date),
                    "execution_date": _date_str(date),
                    "action_type": action_type,
                    "state_before": before_state,
                    "state_after": state,
                    "target_weight_before": before_weight,
                    "target_weight_after": target_weight,
                    "order_notional": order_notional,
                    "execution_price": status["execution_price_reference"],
                    "is_executed": executable,
                    "blocked_reason": blocked_reason,
                    "commission_cost": commission,
                    "stamp_tax_cost": stamp,
                    "slippage_cost": slippage,
                    "cost": action_cost,
                    "cash_weight": 1.0 - actual_weight,
                    "exit_retry_count": pending_exit["retry_count"] if pending_exit else (exit_retry_until + 1 if terminal_blocked else 0),
                    "exit_status": exit_status,
                    "terminal_price_policy": terminal_policy,
                }
            )
        day_net = day_gross - day_cost
        cum_gross = (1.0 + cum_gross) * (1.0 + day_gross) - 1.0
        cum_net = (1.0 + cum_net) * (1.0 + day_net) - 1.0
        if actual_weight > 0 or not pd.isna(first_exposure_date):
            exposures.append(
                {
                    "date": _date_str(date),
                    "schedule_id": schedule_id,
                    "launch_episode_id": str(episode.launch_episode_id),
                    "instrument": instrument,
                    "state": state,
                    "target_weight": target_weight,
                    "actual_weight": actual_weight,
                    "cash_weight": 1.0 - actual_weight,
                    "daily_return_gross": day_gross,
                    "daily_return_net": day_net,
                    "cum_return_gross": cum_gross,
                    "cum_return_net": cum_net,
                }
            )
        if np.isfinite(close_price):
            prev_close = close_price
        if state == "exited" and pending_exit is None and not pd.isna(exited_date):
            break

    no_confirm_reason = ""
    if not confirm_add_enabled:
        no_confirm_reason = "confirm_add_disabled"
    elif confirm is None:
        no_confirm_reason = "no_valid_confirm_candidate_in_window"
    elif not confirm_executed:
        no_confirm_reason = "confirm_candidate_not_executed_before_exit"
    summary = {
        "schedule_id": schedule_id,
        "split": split,
        "launch_episode_id": str(episode.launch_episode_id),
        "instrument": instrument,
        "launch_effective_date": _date_str(episode.launch_effective_date),
        "selected_probe_signal_date": _date_str(probe_signal),
        "selected_probe_execution_date": _date_str(probe_exec),
        "confirm_add_signal_date": _date_str(confirm_signal) if confirm is not None else "",
        "confirm_add_execution_date": _date_str(confirm_exec) if confirm is not None else "",
        "probe_executed": probe_executed,
        "confirm_add_executed": confirm_executed,
        "fast_fail_exit": fast_failed,
        "natural_exit": natural_exited,
        "had_exposure": not pd.isna(first_exposure_date),
        "no_probe": pd.isna(first_exposure_date),
        "confirm_added": confirm_executed,
        "fast_failed": fast_failed,
        "natural_exited": natural_exited,
        "after_cost_return": cum_net if not pd.isna(first_exposure_date) else 0.0,
        "missed_gain_to_exposure": missed_gain_to_exposure,
        "turnover": total_order_notional,
        "first_exposure_date": _date_str(first_exposure_date),
        "exit_date": _date_str(exited_date),
        "selection_status": "selected" if probe_executed else "no_probe",
        "no_probe_reason": "" if probe_executed else "probe_not_executed",
        "no_confirm_add_reason": no_confirm_reason,
        "first_exposure_price": first_exposure_price,
    }
    return {"actions": actions, "exposures": exposures, "summary": summary}


def _summarize_schedule(schedule_id: str, split: str, summaries: pd.DataFrame, baseline_config: dict[str, Any]) -> dict[str, Any]:
    df = summaries.loc[summaries["schedule_id"].eq(schedule_id) & summaries["split"].eq(split)].copy()
    if df.empty:
        return {"schedule_id": schedule_id, "split": split, "episode_count": 0}
    big = base._big_winner_capture(df, baseline_config)
    episode_count = len(df)
    returns = df["after_cost_return"].astype(float)
    exposure = df["had_exposure"].astype(bool)
    top1, top5 = _instrument_concentration(df.loc[exposure])
    positive_count, year_share, inst_year_share = _positive_pnl_concentration(df.loc[exposure])
    return {
        "schedule_id": schedule_id,
        "split": split,
        "episode_count": int(episode_count),
        "episode_with_any_exposure_count": int(exposure.sum()),
        "probe_rate": float(exposure.mean()),
        "confirm_add_rate": float(df["confirm_add_executed"].astype(bool).mean()),
        "fast_fail_exit_rate": float(df["fast_fail_exit"].astype(bool).mean()),
        "natural_exit_rate": float(df["natural_exit"].astype(bool).mean()),
        "mean_after_cost_return": float(returns.mean()),
        "median_after_cost_return": float(returns.median()),
        "p05_after_cost_return": float(returns.quantile(0.05)),
        "p95_after_cost_return": float(returns.quantile(0.95)),
        "big_winner_capture_rate": big["capture_50h120"],
        "missed_gain_to_exposure_median": float(df["missed_gain_to_exposure"].dropna().median()) if df["missed_gain_to_exposure"].notna().any() else np.nan,
        "turnover_proxy": float(df["turnover"].sum() / max(episode_count, 1) * 252.0 / max(int(baseline_config["schedule_defaults"]["primary_H"]), 1)),
        "top1_instrument_year_exposure_share": top1,
        "top5_instrument_exposure_share": top5,
        "positive_pnl_year_count": positive_count,
        "top_year_positive_pnl_share": year_share,
        "top_instrument_year_positive_pnl_share": inst_year_share,
    }


def build_schedule_artifacts(
    config: dict[str, Any],
    paths: RequirementPaths,
    baseline_config: dict[str, Any],
    baseline_paths: base.Paths,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    selected_probe = pd.read_csv(paths.requirement_02_output_root / "reports" / "requirement_02_episode_primary_probe.csv")
    training = pd.read_parquet(paths.requirement_02_output_root / "cache" / "requirement_02_hazard_training_panel.parquet")
    pred = pd.read_parquet(paths.requirement_02_output_root / "cache" / "requirement_02_hazard_prediction_panel.parquet")
    extra_cols = [
        "launch_episode_id",
        "probe_signal_date",
        "probe_execution_date",
        "launch_effective_date",
        "missed_gain_to_probe",
        "pre_probe_fast_fail_from_launch_reference",
        "is_buy_executable_next_open",
        "blocked_buy_reason",
    ]
    candidates = pred.merge(training[extra_cols].drop_duplicates(["launch_episode_id", "probe_signal_date", "probe_execution_date"]), on=["launch_episode_id", "probe_signal_date", "probe_execution_date"], how="left")
    episodes = pd.read_csv(baseline_paths.reports_dir / "ep2_launch_episode_dictionary.csv")
    split_map = selected_probe[["launch_episode_id", "split"]].drop_duplicates()
    episodes = episodes.merge(split_map, on="launch_episode_id", how="inner")
    selected_by_episode = {row.launch_episode_id: pd.Series(row._asdict()) for row in selected_probe.itertuples(index=False)}
    candidate_by_episode = {eid: group.copy() for eid, group in candidates.groupby("launch_episode_id", sort=False)}

    panel = base.load_market_panel(baseline_config)
    lookup = base.price_lookup(panel)
    universe_set = base.universe_membership_set(baseline_config)
    calendar = base.load_calendar(baseline_config)

    schedule_specs = [
        (PRIMARY_SCHEDULE_ID, True, True),
        (R02_REPLAY_SCHEDULE_ID, True, False),
        (NO_FAST_FAIL_SCHEDULE_ID, False, True),
    ]
    action_rows: list[dict[str, Any]] = []
    exposure_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    confirm_rows: list[dict[str, Any]] = []
    for ep in episodes.itertuples(index=False):
        selected = selected_by_episode.get(ep.launch_episode_id)
        group = candidate_by_episode.get(ep.launch_episode_id, pd.DataFrame())
        for schedule_id, fast_fail_enabled, confirm_enabled in schedule_specs:
            result = _simulate_episode(config, baseline_config, calendar, lookup, universe_set, ep, selected, group, ep.split, schedule_id, fast_fail_enabled, confirm_enabled)
            action_rows.extend(result["actions"])
            exposure_rows.extend(result["exposures"])
            summary_rows.append(result["summary"])
        primary = summary_rows[-3]
        confirm_rows.append(
            {
                "split": ep.split,
                "schedule_id": PRIMARY_SCHEDULE_ID,
                "launch_episode_id": ep.launch_episode_id,
                "instrument": ep.instrument,
                "selected_probe_execution_date": primary["selected_probe_execution_date"],
                "confirm_add_execution_date": primary["confirm_add_execution_date"],
                "confirm_add_executed": primary["confirm_add_executed"],
                "no_confirm_add_reason": primary["no_confirm_add_reason"],
            }
        )

    actions = pd.DataFrame(action_rows, columns=base.action_columns())
    exposures = pd.DataFrame(exposure_rows, columns=base.exposure_columns())
    summaries = pd.DataFrame(summary_rows)
    schedule_results = []
    for schedule_id, _, _ in schedule_specs:
        for split in sorted(summaries["split"].dropna().unique()):
            schedule_results.append(_summarize_schedule(schedule_id, split, summaries, baseline_config))
    return actions, exposures, summaries, pd.DataFrame(schedule_results), pd.DataFrame(confirm_rows)


def build_schedule_comparison(config: dict[str, Any], schedule_results: pd.DataFrame, r02_results: pd.DataFrame, baseline_config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    by_key = schedule_results.set_index(["schedule_id", "split"])
    r02_by_split = r02_results.set_index("split")
    for split in sorted(schedule_results["split"].dropna().unique()):
        primary = by_key.loc[(PRIMARY_SCHEDULE_ID, split)]
        r02 = r02_by_split.loc[split]
        replay = by_key.loc[(R02_REPLAY_SCHEDULE_ID, split)]
        no_fast = by_key.loc[(NO_FAST_FAIL_SCHEDULE_ID, split)]
        mean_diff = float(primary.mean_after_cost_return) - float(r02.mean_after_cost_return)
        median_diff = float(primary.median_after_cost_return) - float(r02.median_after_cost_return)
        coverage_loss = 1.0 - float(primary.big_winner_capture_rate) / float(r02.big_winner_capture_rate) if float(r02.big_winner_capture_rate) > 0 else 0.0
        turnover_reduction = 1.0 - float(primary.turnover_proxy) / float(baseline_config["baserate_reference"]["daily_baserate_turnover_proxy"])
        missed_diff = (float(primary.missed_gain_to_exposure_median) if pd.notna(primary.missed_gain_to_exposure_median) else 0.0) - (
            float(r02.missed_gain_to_exposure_median) if pd.notna(r02.missed_gain_to_exposure_median) else 0.0
        )
        rows.append(
            {
                "split": split,
                "schedule_id": PRIMARY_SCHEDULE_ID,
                "comparison_schedule_id": R02_HAZARD_SCHEDULE_ID,
                "mean_after_cost_return_diff": mean_diff,
                "median_after_cost_return_diff": median_diff,
                "big_winner_coverage_loss": coverage_loss,
                "turnover_reduction": turnover_reduction,
                "missed_gain_to_exposure_diff": missed_diff,
                "confirm_add_return_contribution": float(primary.mean_after_cost_return) - float(replay.mean_after_cost_return),
                "fast_fail_return_contribution": float(primary.mean_after_cost_return) - float(no_fast.mean_after_cost_return),
            }
        )
    return pd.DataFrame(rows)


def _filter_baserate(config: dict[str, Any], paths: RequirementPaths) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    br = config["baserate_bridge"]
    pred = pd.read_parquet(paths.base_rate_root / "cache" / "prediction_panel.parquet")
    pred = pred.loc[pred["label_name"].eq(br["primary_label_name"])].copy()
    pred["date"] = pd.to_datetime(pred["date"]).dt.normalize()
    pred["instrument"] = pred["instrument"].astype(str).str.upper()
    pred["base_rate_score_rank_pct"] = pred.groupby("date")["score"].rank(method="max", pct=True)
    pred["base_rate_desc_rank"] = pred.groupby("date")["score"].rank(method="first", ascending=False)
    pred["base_rate_prediction_top50_hit"] = pred["base_rate_desc_rank"].le(int(br["topk_hit_k"]))
    pred["base_rate_high_score_region"] = pred["base_rate_score_rank_pct"].ge(float(br["high_score_quantile"]))

    order = pd.read_parquet(paths.base_rate_root / "cache" / "order_panel.parquet")
    order = order.loc[
        order["portfolio_id"].eq(br["primary_portfolio_id"])
        & order["label_name"].eq(br["primary_label_name"])
        & order["cost_scenario"].eq(br["primary_cost_scenario"])
        & order["side"].eq(br["order_filter"]["side"])
        & order["blocked"].astype(bool).eq(bool(br["order_filter"]["blocked"]))
    ].copy()
    order["date"] = pd.to_datetime(order["date"]).dt.normalize()
    order["instrument"] = order["instrument"].astype(str).str.upper()

    trade = pd.read_parquet(paths.base_rate_root / "cache" / "trade_panel.parquet")
    trade = trade.loc[
        trade["portfolio_id"].eq(br["primary_portfolio_id"])
        & trade["label_name"].eq(br["primary_label_name"])
        & trade["cost_scenario"].eq(br["primary_cost_scenario"])
        & trade["side"].eq(br["trade_filter"]["side"])
        & trade["filled"].astype(bool).eq(bool(br["trade_filter"]["filled"]))
    ].copy()
    trade["date"] = pd.to_datetime(trade["date"]).dt.normalize()
    trade["instrument"] = trade["instrument"].astype(str).str.upper()
    return pred, order, trade


def _primary_events(actions: pd.DataFrame, summaries: pd.DataFrame) -> pd.DataFrame:
    split_map = summaries.loc[summaries["schedule_id"].eq(PRIMARY_SCHEDULE_ID), ["launch_episode_id", "split", "after_cost_return"]].drop_duplicates("launch_episode_id")
    events = actions.loc[
        actions["schedule_id"].eq(PRIMARY_SCHEDULE_ID)
        & actions["action_type"].isin(["probe_entry", "confirm_add"])
        & actions["is_executed"].astype(bool)
    ].copy()
    events = events.merge(split_map, on="launch_episode_id", how="left")
    events["signal_date"] = pd.to_datetime(events["signal_date"]).dt.normalize()
    events["execution_date"] = pd.to_datetime(events["execution_date"]).dt.normalize()
    events["instrument"] = events["instrument"].astype(str).str.upper()
    return events


def build_baserate_reports(
    config: dict[str, Any],
    actions: pd.DataFrame,
    summaries: pd.DataFrame,
    pred: pd.DataFrame,
    order: pd.DataFrame,
    trade: pd.DataFrame,
    baseline_config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    events = _primary_events(actions, summaries)
    pred_key = pred[["date", "instrument", "base_rate_score_rank_pct", "base_rate_high_score_region", "base_rate_prediction_top50_hit"]].copy()
    order_keys = set(zip(order["date"], order["instrument"]))
    trade_keys = set(zip(trade["date"], trade["instrument"]))
    order_dates = set(order["date"])
    trade_dates = set(trade["date"])
    pred_dates = set(pred["date"])

    probe_events = events.loc[events["action_type"].eq("probe_entry")].copy()
    probe_join = probe_events.merge(pred_key, left_on=["signal_date", "instrument"], right_on=["date", "instrument"], how="left")
    launch_rows = []
    for split, group in probe_join.groupby("split", sort=True):
        order_hit = group.apply(lambda r: (r["execution_date"], r["instrument"]) in order_keys, axis=1)
        trade_hit = group.apply(lambda r: (r["execution_date"], r["instrument"]) in trade_keys, axis=1)
        pred_hit = group["base_rate_prediction_top50_hit"].astype("boolean").fillna(False).astype(bool)
        any_hit = pred_hit | order_hit | trade_hit
        count = len(group)
        launch_rows.append(
            {
                "split": split,
                "schedule_id": PRIMARY_SCHEDULE_ID,
                "episode_count": int(summaries.loc[summaries["schedule_id"].eq(PRIMARY_SCHEDULE_ID) & summaries["split"].eq(split), "launch_episode_id"].nunique()),
                "episode_with_probe_count": int(count),
                "base_rate_prediction_covered_count": int(group["base_rate_score_rank_pct"].notna().sum()),
                "base_rate_prediction_coverage_rate": float(group["base_rate_score_rank_pct"].notna().mean()) if count else 0.0,
                "base_rate_prediction_top50_hit_count": int(pred_hit.sum()),
                "base_rate_prediction_top50_hit_rate": float(pred_hit.mean()) if count else 0.0,
                "base_rate_order_hit_count": int(order_hit.sum()),
                "base_rate_order_hit_rate": float(order_hit.mean()) if count else 0.0,
                "base_rate_trade_hit_count": int(trade_hit.sum()),
                "base_rate_trade_hit_rate": float(trade_hit.mean()) if count else 0.0,
                "base_rate_any_hit_count": int(any_hit.sum()),
                "base_rate_any_hit_rate": float(any_hit.mean()) if count else 0.0,
            }
        )

    score_events = events.merge(pred_key, left_on=["signal_date", "instrument"], right_on=["date", "instrument"], how="left")
    score_rows = []
    for (split, action_type), group in score_events.groupby(["split", "action_type"], sort=True):
        covered = group["base_rate_score_rank_pct"].notna()
        top50 = group["base_rate_prediction_top50_hit"].astype("boolean").fillna(False).astype(bool)
        high = group["base_rate_high_score_region"].astype("boolean").fillna(False).astype(bool)
        score_rows.append(
            {
                "split": split,
                "action_type": action_type,
                "event_count": int(len(group)),
                "base_rate_prediction_covered_count": int(covered.sum()),
                "base_rate_prediction_coverage_rate": float(covered.mean()) if len(group) else 0.0,
                "mean_base_rate_score_rank_pct": float(group["base_rate_score_rank_pct"].dropna().mean()) if covered.any() else np.nan,
                "median_base_rate_score_rank_pct": float(group["base_rate_score_rank_pct"].dropna().median()) if covered.any() else np.nan,
                "high_score_region_count": int(high.sum()),
                "high_score_region_rate": float(high.mean()) if len(group) else 0.0,
                "base_rate_prediction_top50_hit_count": int(top50.sum()),
                "base_rate_prediction_top50_hit_rate": float(top50.mean()) if len(group) else 0.0,
            }
        )

    uncovered_rows = []
    primary_summaries = summaries.loc[summaries["schedule_id"].eq(PRIMARY_SCHEDULE_ID)].copy()
    first_event = events.sort_values(["launch_episode_id", "execution_date", "action_type"]).groupby("launch_episode_id", as_index=False).first()
    for split, group in events.groupby("split", sort=True):
        overlap = group.apply(lambda r: ((r["execution_date"], r["instrument"]) in order_keys) or ((r["execution_date"], r["instrument"]) in trade_keys), axis=1)
        uncovered = ~overlap
        uncovered_episode_ids = set(first_event.loc[first_event["split"].eq(split)].loc[
            first_event.loc[first_event["split"].eq(split)].apply(lambda r: not (((r["execution_date"], r["instrument"]) in order_keys) or ((r["execution_date"], r["instrument"]) in trade_keys)), axis=1),
            "launch_episode_id",
        ])
        episode_rows = primary_summaries.loc[primary_summaries["launch_episode_id"].isin(uncovered_episode_ids)]
        big = base._big_winner_capture(episode_rows, baseline_config) if not episode_rows.empty else {"capture_50h120": 0.0}
        turnover_proxy = float(group.loc[uncovered, "order_notional"].sum() / max(primary_summaries.loc[primary_summaries["split"].eq(split), "launch_episode_id"].nunique(), 1) * 252.0 / max(int(baseline_config["schedule_defaults"]["primary_H"]), 1))
        uncovered_rows.append(
            {
                "split": split,
                "schedule_id": PRIMARY_SCHEDULE_ID,
                "executed_ep2_exposure_count": int(len(group)),
                "base_rate_trade_overlap_count": int(overlap.sum()),
                "base_rate_trade_overlap_rate": float(overlap.mean()) if len(group) else 0.0,
                "uncovered_ep2_exposure_count": int(uncovered.sum()),
                "uncovered_ep2_exposure_share": float(uncovered.mean()) if len(group) else 0.0,
                "uncovered_episode_count": int(len(uncovered_episode_ids)),
                "uncovered_episode_share": float(len(uncovered_episode_ids) / max(primary_summaries.loc[primary_summaries["split"].eq(split), "launch_episode_id"].nunique(), 1)),
                "uncovered_mean_after_cost_return": float(episode_rows["after_cost_return"].astype(float).mean()) if not episode_rows.empty else 0.0,
                "uncovered_big_winner_capture_rate": float(big["capture_50h120"]),
                "uncovered_turnover_proxy": turnover_proxy,
            }
        )

    coverage_rows = []
    eligible = events.loc[events["split"].isin(["validation", "robustness"])].copy()
    for split, group in eligible.groupby("split", sort=True):
        pred_cov = group.apply(lambda r: (r["signal_date"] in pred_dates) and not pred_key.loc[(pred_key["date"].eq(r["signal_date"])) & (pred_key["instrument"].eq(r["instrument"]))].empty, axis=1)
        order_cov = group["execution_date"].isin(order_dates)
        trade_cov = group["execution_date"].isin(trade_dates)
        coverage_rows.append(
            {
                "split": split,
                "eligible_ep2_action_count": int(len(group)),
                "prediction_coverage_rate": float(pred_cov.mean()) if len(group) else 0.0,
                "order_coverage_rate": float(order_cov.mean()) if len(group) else 0.0,
                "trade_coverage_rate": float(trade_cov.mean()) if len(group) else 0.0,
                "baserate_overlap_report_coverage": float(min(pred_cov.mean(), order_cov.mean(), trade_cov.mean())) if len(group) else 0.0,
            }
        )
    return pd.DataFrame(launch_rows), pd.DataFrame(score_rows), pd.DataFrame(uncovered_rows), pd.DataFrame(coverage_rows)


def build_gate_audit(
    config: dict[str, Any],
    schedule_results: pd.DataFrame,
    comparison: pd.DataFrame,
    coverage: pd.DataFrame,
    uncovered: pd.DataFrame,
    leakage: pd.DataFrame,
) -> tuple[pd.DataFrame, str]:
    gate_cfg = config["proceed_gate"]
    rows: list[dict[str, Any]] = []

    def add(split: str, gate_name: str, value: Any, threshold: Any, passed: bool, category: str, comparison_id: str = "self") -> None:
        rows.append(
            {
                "split": split,
                "schedule_id": PRIMARY_SCHEDULE_ID,
                "gate_name": gate_name,
                "gate_value": value,
                "threshold_value": threshold,
                "comparison_id": comparison_id,
                "passed": bool(passed),
                "failure_reason": "" if passed else "gate_failed",
                "is_hard_stop": True,
                "failure_category": category,
            }
        )

    add("all", "frozen_contract_and_leakage_audit", bool(leakage["passed"].astype(bool).all()), True, bool(leakage["passed"].astype(bool).all()), "contract_or_leakage")
    cmp_by_split = comparison.set_index("split")
    res_by_split = schedule_results.loc[schedule_results["schedule_id"].eq(PRIMARY_SCHEDULE_ID)].set_index("split")
    cov_by_split = coverage.set_index("split") if not coverage.empty else pd.DataFrame()
    unc_by_split = uncovered.set_index("split") if not uncovered.empty else pd.DataFrame()
    for split in ["validation", "robustness"]:
        if split not in cmp_by_split.index or split not in res_by_split.index:
            add(split, "required_split_present", False, True, False, "schedule")
            continue
        cmp_row = cmp_by_split.loc[split]
        res_row = res_by_split.loc[split]
        mean_threshold = float(gate_cfg["min_validation_mean_after_cost_return_diff_vs_requirement_02"]) if split == "validation" else float(gate_cfg["min_robustness_mean_after_cost_return_diff_vs_requirement_02"])
        mean_pass = float(cmp_row.mean_after_cost_return_diff) > mean_threshold if split == "validation" else float(cmp_row.mean_after_cost_return_diff) >= mean_threshold
        add(split, "mean_after_cost_return_diff_vs_requirement_02", cmp_row.mean_after_cost_return_diff, mean_threshold, mean_pass, "schedule", R02_HAZARD_SCHEDULE_ID)
        add(split, "big_winner_coverage_loss_vs_requirement_02", cmp_row.big_winner_coverage_loss, gate_cfg["max_big_winner_coverage_loss_vs_requirement_02"], float(cmp_row.big_winner_coverage_loss) <= float(gate_cfg["max_big_winner_coverage_loss_vs_requirement_02"]), "schedule", R02_HAZARD_SCHEDULE_ID)
        add(split, "missed_gain_to_exposure_median", res_row.missed_gain_to_exposure_median if pd.notna(res_row.missed_gain_to_exposure_median) else 0.0, gate_cfg["max_missed_gain_to_exposure_median"], (pd.isna(res_row.missed_gain_to_exposure_median) or float(res_row.missed_gain_to_exposure_median) <= float(gate_cfg["max_missed_gain_to_exposure_median"])), "schedule")
        add(split, "turnover_reduction_vs_daily_baserate", cmp_row.turnover_reduction, gate_cfg["min_turnover_reduction_vs_daily_baserate"], float(cmp_row.turnover_reduction) >= float(gate_cfg["min_turnover_reduction_vs_daily_baserate"]), "schedule")
        add(split, "top1_instrument_year_exposure_share", res_row.top1_instrument_year_exposure_share, gate_cfg["max_top1_instrument_year_exposure_share"], float(res_row.top1_instrument_year_exposure_share) <= float(gate_cfg["max_top1_instrument_year_exposure_share"]), "schedule")
        add(split, "top5_instrument_exposure_share", res_row.top5_instrument_exposure_share, gate_cfg["max_top5_instrument_exposure_share"], float(res_row.top5_instrument_exposure_share) <= float(gate_cfg["max_top5_instrument_exposure_share"]), "schedule")
        cov_value = cov_by_split.loc[split, "baserate_overlap_report_coverage"] if split in cov_by_split.index else 0.0
        add(split, "baserate_overlap_report_coverage", cov_value, gate_cfg["min_baserate_overlap_report_coverage"], float(cov_value) >= float(gate_cfg["min_baserate_overlap_report_coverage"]), "baserate")
        unc_value = unc_by_split.loc[split, "uncovered_ep2_exposure_share"] if split in unc_by_split.index else 0.0
        add(split, "uncovered_ep2_exposure_share", unc_value, gate_cfg["min_uncovered_ep2_exposure_share"], float(unc_value) >= float(gate_cfg["min_uncovered_ep2_exposure_share"]), "baserate")

    gate_df = pd.DataFrame(rows)
    if not bool(gate_df.loc[gate_df["failure_category"].eq("contract_or_leakage"), "passed"].astype(bool).all()):
        status = "failed_contract_or_leakage"
    elif not bool(gate_df.loc[gate_df["failure_category"].eq("schedule"), "passed"].astype(bool).all()):
        status = "failed_schedule_bridge"
    elif not bool(gate_df.loc[gate_df["failure_category"].eq("baserate"), "passed"].astype(bool).all()):
        status = "failed_baserate_bridge_coverage"
    else:
        status = "passed"
    return gate_df, status


def _authority_row(name: str, path: Path, role: str, producer: str) -> dict[str, Any]:
    row_count = np.nan
    if path.exists() and path.suffix == ".csv":
        row_count = len(pd.read_csv(path))
    elif path.exists() and path.suffix == ".parquet":
        row_count = len(pd.read_parquet(path))
    elif path.exists() and path.suffix == ".json":
        row_count = 1
    return {
        "artifact_name": name,
        "artifact_path": relpath(path),
        "authority_role": role,
        "producer_command": producer,
        "schema_version": SCHEMA_VERSION,
        "required_for_requirement": True,
        "row_count": row_count,
        "content_hash": file_hash(path) if path.exists() else "",
    }


def write_artifact_authority(paths: RequirementPaths) -> pd.DataFrame:
    producer = "uv run python ep2/scripts/run_requirement_03_schedule_bridge.py --config ep2/configs/requirement_03_schedule_bridge.yaml"
    rows = []
    for name in REQUIRED_CACHE:
        rows.append(_authority_row(name, paths.cache_dir / name, "cache", producer))
    for name in REQUIRED_REPORTS:
        if name == "requirement_03_artifact_authority.csv":
            continue
        rows.append(_authority_row(name, paths.reports_dir / name, "report", producer))
    for name in REQUIRED_MANIFESTS:
        rows.append(_authority_row(name, paths.manifests_dir / name, "manifest", producer))
    authority = pd.DataFrame(rows)
    write_csv(authority, paths.reports_dir / "requirement_03_artifact_authority.csv")
    return authority


def run_requirement_03(config_path: str | Path) -> dict[str, Any]:
    config, paths, baseline_config, baseline_paths = load_requirement_config(config_path)
    stage = StageAudit()
    r02_state = assert_requirement_02_entry(config)
    stage.add("load_requirement_02_selected_contract", 1, "requirement_02_hazard_manifest.json", r02_state["manifest_hash"], base_rate_rows_available=False)
    stage.add("build_fixed_schedule_bridge_rule", 2, "requirement_03_schedule_bridge.yaml", file_hash(paths.config_path), base_rate_rows_available=False)

    actions, exposures, summaries, schedule_results, confirm_audit = build_schedule_artifacts(config, paths, baseline_config, baseline_paths)
    write_parquet(actions, paths.cache_dir / "requirement_03_schedule_action_panel.parquet")
    action_hash_before = file_hash(paths.cache_dir / "requirement_03_schedule_action_panel.parquet")
    stage.add("generate_ep2_schedule_action_panel", 3, output_artifact_name="requirement_03_schedule_action_panel.parquet", output_artifact_hash=action_hash_before, base_rate_rows_available=False)
    write_parquet(exposures, paths.cache_dir / "requirement_03_exposure_daily_panel.parquet")
    exposure_hash_before = file_hash(paths.cache_dir / "requirement_03_exposure_daily_panel.parquet")
    stage.add("generate_ep2_exposure_daily_panel", 4, output_artifact_name="requirement_03_exposure_daily_panel.parquet", output_artifact_hash=exposure_hash_before, base_rate_rows_available=False)
    write_parquet(summaries, paths.cache_dir / "requirement_03_episode_schedule_summary.parquet")
    write_csv(schedule_results, paths.reports_dir / "requirement_03_schedule_results.csv")
    write_csv(confirm_audit, paths.reports_dir / "requirement_03_confirm_add_audit.csv")

    pred, order, trade = _filter_baserate(config, paths)
    stage.add("load_filtered_baserate_prediction_panel", 5, input_artifact_name="prediction_panel.parquet", input_artifact_hash=file_hash(paths.base_rate_root / "cache" / "prediction_panel.parquet"), base_rate_rows_available=True)
    stage.add("load_filtered_baserate_order_panel", 6, input_artifact_name="order_panel.parquet", input_artifact_hash=file_hash(paths.base_rate_root / "cache" / "order_panel.parquet"), base_rate_rows_available=True)
    stage.add("load_filtered_baserate_trade_panel", 7, input_artifact_name="trade_panel.parquet", input_artifact_hash=file_hash(paths.base_rate_root / "cache" / "trade_panel.parquet"), base_rate_rows_available=True)
    action_hash_after = file_hash(paths.cache_dir / "requirement_03_schedule_action_panel.parquet")
    exposure_hash_after = file_hash(paths.cache_dir / "requirement_03_exposure_daily_panel.parquet")

    r02_results = pd.read_csv(paths.requirement_02_output_root / "reports" / "requirement_02_schedule_results.csv")
    comparison = build_schedule_comparison(config, schedule_results, r02_results, baseline_config)
    write_csv(comparison, paths.reports_dir / "requirement_03_schedule_comparison.csv")
    launch_overlap, score_overlap, uncovered, coverage = build_baserate_reports(config, actions, summaries, pred, order, trade, baseline_config)
    write_csv(launch_overlap, paths.reports_dir / "requirement_03_baserate_launch_overlap.csv")
    write_csv(score_overlap, paths.reports_dir / "requirement_03_baserate_score_overlap.csv")
    write_csv(uncovered, paths.reports_dir / "requirement_03_baserate_uncovered_opportunity.csv")
    write_csv(coverage, paths.reports_dir / "requirement_03_baserate_coverage_gate.csv")
    stage.add("generate_baserate_overlap_reports", 8, output_artifact_name="requirement_03_baserate_launch_overlap.csv", output_artifact_hash=file_hash(paths.reports_dir / "requirement_03_baserate_launch_overlap.csv"), base_rate_rows_available=True)

    leakage = pd.DataFrame(
        [
            ("requirement_02_threshold_unchanged", _same_float(r02_state["manifest"]["selected_threshold"], config["frozen_contract"]["selected_threshold"]), r02_state["manifest"]["selected_threshold"], config["frozen_contract"]["selected_threshold"]),
            ("requirement_02_stop_risk_ceiling_unchanged", _same_float(r02_state["manifest"]["selected_stop_risk_ceiling"], config["frozen_contract"]["selected_stop_risk_ceiling"]), r02_state["manifest"]["selected_stop_risk_ceiling"], config["frozen_contract"]["selected_stop_risk_ceiling"]),
            ("base_rate_not_used_for_probe_selection", True, "not_loaded_until_stage_5", "base_rate_rows_unavailable_stages_1_4"),
            ("base_rate_not_used_for_confirm_add_selection", True, "confirm_rule_from_config_and_r02", "no_baserate_inputs"),
            ("base_rate_not_used_for_feature_construction", True, "no_features_constructed", "no_baserate_inputs"),
            ("base_rate_not_used_for_label_selection", True, "r02_label_frozen", "no_baserate_inputs"),
            ("base_rate_not_used_for_schedule_selection", True, "schedule_hash_before_after_check", "unchanged"),
            ("base_rate_portfolio_return_not_used_as_gate", True, "no_portfolio_return_gate", "not_used"),
            ("stage_order_prevents_baserate_pre_schedule_access", True, "stages_1_4_false", "true"),
            ("schedule_action_panel_hash_unchanged_after_baserate_load", action_hash_after == action_hash_before, action_hash_after, action_hash_before),
            ("exposure_daily_panel_hash_unchanged_after_baserate_load", exposure_hash_after == exposure_hash_before, exposure_hash_after, exposure_hash_before),
        ],
        columns=["audit_name", "passed", "observed_value", "expected_value"],
    )
    leakage["detail"] = np.where(leakage["passed"].astype(bool), "", "audit_failed")
    write_csv(leakage, paths.reports_dir / "requirement_03_baserate_leakage_audit.csv")

    gate_audit, status = build_gate_audit(config, schedule_results, comparison, coverage, uncovered, leakage)
    write_csv(gate_audit, paths.reports_dir / "requirement_03_gate_audit.csv")
    stage.add("evaluate_requirement_03_gates", 9, output_artifact_name="requirement_03_gate_audit.csv", output_artifact_hash=file_hash(paths.reports_dir / "requirement_03_gate_audit.csv"), base_rate_rows_available=True)
    write_csv(stage.frame(), paths.reports_dir / "requirement_03_stage_order_audit.csv")

    base_rate_manifest = paths.base_rate_root / "reports" / "base_rate_run_manifest.json"
    manifest = {
        "phase": config["phase"],
        "validation_status": status,
        "next_phase_proceed_status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requirement_02_manifest_hash": r02_state["manifest_hash"],
        "engineering_baseline_manifest_hash": file_hash(paths.baseline_output_root / "manifests" / "ep2_engineering_baseline_manifest.json"),
        "base_rate_manifest_hash": file_hash(base_rate_manifest),
        "primary_label_id": config["frozen_contract"]["primary_label_id"],
        "frozen_baseline_id": config["frozen_contract"]["frozen_baseline_id"],
        "hazard_schedule_id": config["frozen_contract"]["hazard_schedule_id"],
        "schedule_bridge_id": config["schedule_bridge"]["schedule_id"],
        "selected_threshold": config["frozen_contract"]["selected_threshold"],
        "selected_stop_risk_ceiling": config["frozen_contract"]["selected_stop_risk_ceiling"],
        "schedule_action_panel_hash": action_hash_before,
        "exposure_daily_panel_hash": exposure_hash_before,
        "schedule_results_hash": file_hash(paths.reports_dir / "requirement_03_schedule_results.csv"),
        "schedule_comparison_hash": file_hash(paths.reports_dir / "requirement_03_schedule_comparison.csv"),
        "baserate_launch_overlap_hash": file_hash(paths.reports_dir / "requirement_03_baserate_launch_overlap.csv"),
        "baserate_score_overlap_hash": file_hash(paths.reports_dir / "requirement_03_baserate_score_overlap.csv"),
        "baserate_uncovered_opportunity_hash": file_hash(paths.reports_dir / "requirement_03_baserate_uncovered_opportunity.csv"),
        "baserate_leakage_audit_hash": file_hash(paths.reports_dir / "requirement_03_baserate_leakage_audit.csv"),
        "stage_order_audit_hash": file_hash(paths.reports_dir / "requirement_03_stage_order_audit.csv"),
        "gate_audit_hash": file_hash(paths.reports_dir / "requirement_03_gate_audit.csv"),
    }
    write_json(manifest, paths.manifests_dir / "requirement_03_schedule_bridge_manifest.json")
    write_artifact_authority(paths)
    return {
        "phase": config["phase"],
        "validation_status": status,
        "next_phase_proceed_status": status,
        "output_root": relpath(paths.output_root),
    }


def validate_requirement_03(config_path: str | Path, fail_on_gate_status: bool = True) -> dict[str, Any]:
    config, paths, baseline_config, _ = load_requirement_config(config_path)
    failures: list[str] = []
    try:
        assert_requirement_02_entry(config)
    except Exception as exc:
        failures.append(str(exc))

    required_paths = [paths.cache_dir / name for name in REQUIRED_CACHE]
    required_paths += [paths.reports_dir / name for name in REQUIRED_REPORTS]
    required_paths += [paths.manifests_dir / name for name in REQUIRED_MANIFESTS]
    for path in required_paths:
        if not path.exists():
            failures.append(f"missing required artifact: {relpath(path)}")
    if failures:
        raise SystemExit("Requirement 03 validation failed:\n" + "\n".join(failures))

    manifest_path = paths.manifests_dir / "requirement_03_schedule_bridge_manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("phase") != config["phase"]:
        failures.append("manifest phase mismatch")
    if manifest.get("schedule_bridge_id") != config["schedule_bridge"]["schedule_id"]:
        failures.append("manifest schedule_bridge_id mismatch")
    if not _same_float(manifest.get("selected_threshold"), config["frozen_contract"]["selected_threshold"]):
        failures.append("manifest selected_threshold mismatch")
    if not _same_float(manifest.get("selected_stop_risk_ceiling"), config["frozen_contract"]["selected_stop_risk_ceiling"]):
        failures.append("manifest selected_stop_risk_ceiling mismatch")

    actions = pd.read_parquet(paths.cache_dir / "requirement_03_schedule_action_panel.parquet")
    exposures = pd.read_parquet(paths.cache_dir / "requirement_03_exposure_daily_panel.parquet")
    summaries = pd.read_parquet(paths.cache_dir / "requirement_03_episode_schedule_summary.parquet")
    missing_action = set(base.action_columns()) - set(actions.columns)
    missing_exposure = set(base.exposure_columns()) - set(exposures.columns)
    if missing_action:
        failures.append(f"schedule action schema missing columns: {sorted(missing_action)}")
    if missing_exposure:
        failures.append(f"exposure schema missing columns: {sorted(missing_exposure)}")
    if summaries["launch_episode_id"].duplicated().all():
        failures.append("episode summary appears invalid")

    stage = pd.read_csv(paths.reports_dir / "requirement_03_stage_order_audit.csv")
    expected_stages = [
        "load_requirement_02_selected_contract",
        "build_fixed_schedule_bridge_rule",
        "generate_ep2_schedule_action_panel",
        "generate_ep2_exposure_daily_panel",
        "load_filtered_baserate_prediction_panel",
        "load_filtered_baserate_order_panel",
        "load_filtered_baserate_trade_panel",
        "generate_baserate_overlap_reports",
        "evaluate_requirement_03_gates",
    ]
    if list(stage.sort_values("stage_order")["stage_name"]) != expected_stages:
        failures.append("stage order audit does not match required stage order")
    early = stage.loc[stage["stage_order"].astype(int).le(4)]
    if bool(early["base_rate_rows_available"].astype(bool).any()):
        failures.append("BaseRate rows available before EP2 schedule artifacts were generated")

    leakage = pd.read_csv(paths.reports_dir / "requirement_03_baserate_leakage_audit.csv")
    if not bool(leakage["passed"].astype(bool).all()):
        failures.append("BaseRate leakage audit has failed rows")
    required_leakage = {
        "requirement_02_threshold_unchanged",
        "requirement_02_stop_risk_ceiling_unchanged",
        "base_rate_not_used_for_probe_selection",
        "base_rate_not_used_for_confirm_add_selection",
        "base_rate_not_used_for_feature_construction",
        "base_rate_not_used_for_label_selection",
        "base_rate_not_used_for_schedule_selection",
        "base_rate_portfolio_return_not_used_as_gate",
        "stage_order_prevents_baserate_pre_schedule_access",
        "schedule_action_panel_hash_unchanged_after_baserate_load",
        "exposure_daily_panel_hash_unchanged_after_baserate_load",
    }
    if set(leakage["audit_name"]) != required_leakage:
        failures.append("BaseRate leakage audit row set mismatch")

    coverage = pd.read_csv(paths.reports_dir / "requirement_03_baserate_coverage_gate.csv")
    if set(coverage["split"]) != {"validation", "robustness"}:
        failures.append("BaseRate coverage gate must report validation and robustness only")
    gate_cfg = config["proceed_gate"]
    if not coverage["baserate_overlap_report_coverage"].ge(float(gate_cfg["min_baserate_overlap_report_coverage"])).all():
        failures.append("BaseRate overlap coverage gate failed")

    score = pd.read_csv(paths.reports_dir / "requirement_03_baserate_score_overlap.csv")
    if "mean_base_rate_score_rank_pct" not in score or score["mean_base_rate_score_rank_pct"].dropna().lt(0).any() or score["mean_base_rate_score_rank_pct"].dropna().gt(1).any():
        failures.append("BaseRate score rank pct invalid")
    uncovered = pd.read_csv(paths.reports_dir / "requirement_03_baserate_uncovered_opportunity.csv")
    if not uncovered["uncovered_ep2_exposure_share"].ge(float(gate_cfg["min_uncovered_ep2_exposure_share"])).all():
        failures.append("uncovered EP2 exposure share gate failed")

    for key, rel in {
        "schedule_action_panel_hash": paths.cache_dir / "requirement_03_schedule_action_panel.parquet",
        "exposure_daily_panel_hash": paths.cache_dir / "requirement_03_exposure_daily_panel.parquet",
        "schedule_results_hash": paths.reports_dir / "requirement_03_schedule_results.csv",
        "schedule_comparison_hash": paths.reports_dir / "requirement_03_schedule_comparison.csv",
        "baserate_launch_overlap_hash": paths.reports_dir / "requirement_03_baserate_launch_overlap.csv",
        "baserate_score_overlap_hash": paths.reports_dir / "requirement_03_baserate_score_overlap.csv",
        "baserate_uncovered_opportunity_hash": paths.reports_dir / "requirement_03_baserate_uncovered_opportunity.csv",
        "baserate_leakage_audit_hash": paths.reports_dir / "requirement_03_baserate_leakage_audit.csv",
        "stage_order_audit_hash": paths.reports_dir / "requirement_03_stage_order_audit.csv",
        "gate_audit_hash": paths.reports_dir / "requirement_03_gate_audit.csv",
    }.items():
        if manifest.get(key) != file_hash(rel):
            failures.append(f"manifest hash mismatch: {key}")

    gates = pd.read_csv(paths.reports_dir / "requirement_03_gate_audit.csv")
    if fail_on_gate_status and not bool(gates.loc[gates["is_hard_stop"].astype(bool), "passed"].astype(bool).all()):
        failures.append("Requirement 03 hard gates did not all pass")
    if manifest.get("next_phase_proceed_status") == "passed" and not bool(gates.loc[gates["is_hard_stop"].astype(bool), "passed"].astype(bool).all()):
        failures.append("manifest passed despite failed hard gates")
    if failures:
        manifest["validation_status"] = manifest.get("validation_status", "failed_validation")
        raise SystemExit("Requirement 03 validation failed:\n" + "\n".join(failures))
    return {
        "phase": config["phase"],
        "validation_status": manifest.get("validation_status"),
        "next_phase_proceed_status": manifest.get("next_phase_proceed_status"),
        "gate_count": int(len(gates)),
        "passed_gate_count": int(gates["passed"].astype(bool).sum()),
        "failed_gate_count": int((~gates["passed"].astype(bool)).sum()),
        "output_root": relpath(paths.output_root),
    }
