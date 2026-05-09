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


SCHEMA_VERSION = "requirement_04_holding_exit_winner_capture_extension_v1"
R03_PRIMARY = "hazard_probe_confirm_add_fast_fail"
BASELINE_SCHEDULE = "R03_original_H10"
BASE_VARIANT = "base"
PROMOTION_VARIANTS = {
    "R03_confirmed_H20": ("primary", "h20", 20),
    "R03_confirmed_H60": ("primary", "h60", 60),
    "R03_confirmed_H120": ("primary", "h120", 120),
    "R03_winner_state_hold_H120": ("primary", "winner_state_base", 120),
}
DIAGNOSTIC_VARIANTS = {
    "R03_all_H20": ("diagnostic", "all_h20", 20),
    "R03_all_H40": ("diagnostic", "all_h40", 40),
    "R03_confirmed_H40": ("diagnostic", "confirmed_h40", 40),
    "R03_no_fast_fail": ("diagnostic", "no_fast_fail", 10),
    "R03_relaxed_fast_fail": ("diagnostic", "relaxed_fast_fail", 10),
}
COMPLEXITY_ORDER = ["R03_confirmed_H20", "R03_confirmed_H60", "R03_confirmed_H120", "R03_winner_state_hold_H120"]

REQUIRED_CACHE = [
    "requirement_04_schedule_action_panel.parquet",
    "requirement_04_exposure_daily_panel.parquet",
    "requirement_04_episode_schedule_summary.parquet",
    "requirement_04_winner_state_event_panel.parquet",
]
REQUIRED_REPORTS = [
    "requirement_04_schedule_results.csv",
    "requirement_04_schedule_comparison.csv",
    "requirement_04_selected_schedule.csv",
    "requirement_04_big_winner_capture_audit.csv",
    "requirement_04_fast_fail_value_audit.csv",
    "requirement_04_winner_state_asof_audit.csv",
    "requirement_04_diagnostic_counterfactuals.csv",
    "requirement_04_gate_audit.csv",
    "requirement_04_artifact_authority.csv",
]
REQUIRED_MANIFESTS = ["requirement_04_holding_exit_manifest.json"]


@dataclass(frozen=True)
class RequirementPaths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    reports_dir: Path
    manifests_dir: Path
    baseline_config_path: Path
    baseline_output_root: Path
    requirement_03_output_root: Path
    requirement_02_output_root: Path


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
        requirement_03_output_root=topic_path(config["inputs"]["requirement_03_output_root"]),
        requirement_02_output_root=topic_path(config["inputs"]["requirement_02_output_root"]),
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
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return bool(value)


def assert_requirement_03_entry(config: dict[str, Any]) -> dict[str, Any]:
    frozen = config["frozen_contract"]
    manifest_path = topic_path(frozen["requirement_03_manifest"])
    gate_path = topic_path(frozen["requirement_03_gate_audit"])
    if not manifest_path.exists():
        raise RuntimeError(f"missing Requirement 03 manifest: {relpath(manifest_path)}")
    if not gate_path.exists():
        raise RuntimeError(f"missing Requirement 03 gate audit: {relpath(gate_path)}")
    manifest = read_json(manifest_path)
    checks = {
        "phase": "requirement_03_schedule_bridge",
        "validation_status": frozen["expected_requirement_03_status"],
        "next_phase_proceed_status": frozen["expected_requirement_03_next_phase_status"],
        "primary_label_id": frozen["primary_label_id"],
        "frozen_baseline_id": frozen["frozen_baseline_id"],
        "hazard_schedule_id": frozen["hazard_schedule_id"],
        "schedule_bridge_id": frozen["schedule_bridge_id"],
    }
    failures = [f"Requirement 03 {key} expected {expected}, observed {manifest.get(key)}" for key, expected in checks.items() if manifest.get(key) != expected]
    if not _same_float(manifest.get("selected_threshold"), frozen["selected_threshold"]):
        failures.append("Requirement 03 selected_threshold mismatch")
    if not _same_float(manifest.get("selected_stop_risk_ceiling"), frozen["selected_stop_risk_ceiling"]):
        failures.append("Requirement 03 selected_stop_risk_ceiling mismatch")
    gates = pd.read_csv(gate_path)
    gate_count = int(len(gates))
    passed_count = int(gates["passed"].astype(bool).sum()) if "passed" in gates else 0
    failed_count = gate_count - passed_count
    if gate_count != int(frozen["requirement_03_expected_gate_count"]):
        failures.append(f"Requirement 03 gate_count expected {frozen['requirement_03_expected_gate_count']}, observed {gate_count}")
    if passed_count != int(frozen["requirement_03_expected_passed_gate_count"]):
        failures.append(f"Requirement 03 passed_gate_count expected {frozen['requirement_03_expected_passed_gate_count']}, observed {passed_count}")
    if failed_count != int(frozen["requirement_03_expected_failed_gate_count"]):
        failures.append(f"Requirement 03 failed_gate_count expected {frozen['requirement_03_expected_failed_gate_count']}, observed {failed_count}")
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


def _action_priority(action_type: str) -> int:
    return {
        "fast_fail_exit": 0,
        "trailing_exit": 1,
        "profit_floor_exit": 1,
        "confirm_add_price_floor_exit": 1,
        "natural_exit": 2,
        "probe_entry": 3,
        "confirm_add": 4,
        "winner_state_enter": 5,
        "blocked_action": 6,
    }.get(action_type, 99)


def _variant_catalog(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [{"schedule_id": BASELINE_SCHEDULE, "variant_id": BASE_VARIANT, "schedule_role": "baseline", "parameter_name": "", "parameter_value": np.nan}]
    for sid, (role, vid, h_days) in PROMOTION_VARIANTS.items():
        rows.append({"schedule_id": sid, "variant_id": vid, "schedule_role": role, "parameter_name": "natural_exit_H", "parameter_value": h_days})
    for sid, (role, vid, h_days) in DIAGNOSTIC_VARIANTS.items():
        rows.append({"schedule_id": sid, "variant_id": vid, "schedule_role": role, "parameter_name": "natural_exit_H", "parameter_value": h_days})
    for threshold in config["diagnostic_sensitivity"]["winner_state_gain_thresholds"]:
        rows.append(
            {
                "schedule_id": "winner_state_gain_threshold_sensitivity",
                "variant_id": f"gain_{int(float(threshold) * 100):02d}",
                "schedule_role": "diagnostic",
                "parameter_name": "min_close_return_from_first_exposure",
                "parameter_value": float(threshold),
            }
        )
    for trailing in config["diagnostic_sensitivity"]["winner_state_trailing_drawdowns"]:
        rows.append(
            {
                "schedule_id": "winner_state_trailing_sensitivity",
                "variant_id": f"trailing_{int(float(trailing) * 100):02d}",
                "schedule_role": "diagnostic",
                "parameter_name": "trailing_drawdown_from_post_winner_high_close",
                "parameter_value": float(trailing),
            }
        )
    return rows


def compute_price_authority(config: dict[str, Any], baseline_config: dict[str, Any], episodes: pd.DataFrame, panel: pd.DataFrame, calendar: pd.DatetimeIndex) -> dict[str, Any]:
    instruments = sorted(episodes["instrument"].astype(str).str.upper().unique())
    min_date = pd.to_datetime(episodes["launch_effective_date"], errors="coerce").min()
    max_launch = pd.to_datetime(episodes["launch_effective_date"], errors="coerce").max()
    max_date = base.add_trading_days(calendar, max_launch, 240)
    if pd.isna(max_date):
        max_date = calendar[-1]
    scope = panel.loc[
        panel["instrument"].isin(instruments)
        & panel["datetime"].ge(min_date)
        & panel["datetime"].le(max_date),
        ["instrument", "datetime", "open", "high", "low", "close", "volume", "money"],
    ].copy()
    scope["datetime"] = pd.to_datetime(scope["datetime"]).dt.strftime("%Y-%m-%d")
    scope = scope.sort_values(["instrument", "datetime"]).reset_index(drop=True)
    digest = hashlib.sha256()
    digest.update(",".join(scope.columns).encode("utf-8"))
    scope.to_csv(None, index=False)
    digest.update(scope.to_csv(index=False).encode("utf-8"))
    cal_values = [d.date().isoformat() for d in calendar[(calendar >= min_date) & (calendar <= max_date)]]
    calendar_hash = canonical_hash(cal_values)
    return {
        "pit_price_source_hash": digest.hexdigest(),
        "pit_calendar_hash": calendar_hash,
        "pit_price_field_schema_version": config["pit_price_authority"]["price_field_schema_version"],
        "pit_price_hash_scope": config["pit_price_authority"]["hash_scope"],
        "pit_price_hash_scope_start": _date_str(min_date),
        "pit_price_hash_scope_end": _date_str(max_date),
        "pit_price_hash_instrument_count": int(len(instruments)),
        "pit_price_hash_row_count": int(len(scope)),
    }


def _target_dates_for_episode(
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    calendar: pd.DatetimeIndex,
    instrument: str,
    launch_date: pd.Timestamp,
    target: float,
    horizon: int,
) -> pd.Timestamp | pd.NaT:
    launch_open = float(lookup.get((instrument, launch_date), {}).get("open", np.nan))
    if not np.isfinite(launch_open) or launch_open <= 0:
        return pd.NaT
    for date in calendar[(calendar >= launch_date)][: int(horizon)]:
        high = float(lookup.get((instrument, pd.Timestamp(date)), {}).get("high", np.nan))
        if np.isfinite(high) and high / launch_open - 1.0 >= float(target):
            return pd.Timestamp(date)
    return pd.NaT


def build_big_winner_targets(baseline_config: dict[str, Any], lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]], calendar: pd.DatetimeIndex, episodes: pd.DataFrame) -> pd.DataFrame:
    p = baseline_config["big_winner"]["primary"]
    s = baseline_config["big_winner"]["sensitivity"]
    rows = []
    for ep in episodes.itertuples(index=False):
        launch = _as_date_or_nat(ep.launch_effective_date)
        inst = str(ep.instrument).upper()
        t50 = _target_dates_for_episode(lookup, calendar, inst, launch, float(p["upside_target"]), int(p["horizon_days"]))
        t100 = _target_dates_for_episode(lookup, calendar, inst, launch, float(s["upside_target"]), int(s["horizon_days"]))
        rows.append(
            {
                "launch_episode_id": str(ep.launch_episode_id),
                "instrument": inst,
                "launch_effective_date": _date_str(launch),
                "first_50pct_target_date": _date_str(t50),
                "first_100pct_target_date": _date_str(t100),
                "big_winner_50h120": not pd.isna(t50),
                "big_winner_100h240": not pd.isna(t100),
            }
        )
    return pd.DataFrame(rows)


def _empty_summary(source: pd.Series, schedule_id: str, variant_id: str, role: str) -> dict[str, Any]:
    return {
        "schedule_id": schedule_id,
        "variant_id": variant_id,
        "schedule_role": role,
        "split": source.get("split", ""),
        "launch_episode_id": str(source.get("launch_episode_id", "")),
        "instrument": str(source.get("instrument", "")).upper(),
        "launch_effective_date": _date_str(source.get("launch_effective_date", "")),
        "selected_probe_signal_date": _date_str(source.get("selected_probe_signal_date", "")),
        "selected_probe_execution_date": _date_str(source.get("selected_probe_execution_date", "")),
        "confirm_add_signal_date": _date_str(source.get("confirm_add_signal_date", "")),
        "confirm_add_execution_date": _date_str(source.get("confirm_add_execution_date", "")),
        "probe_executed": False,
        "confirm_add_executed": False,
        "winner_state_entered": False,
        "winner_state_signal_date": "",
        "winner_state_effective_date": "",
        "winner_state_transition_price": np.nan,
        "first_exposure_date": "",
        "first_exposure_price": np.nan,
        "confirm_add_price": np.nan,
        "exit_date": "",
        "exit_reason": "",
        "exit_target_weight_after": 0.0,
        "natural_exit_clock_start_date": "",
        "natural_exit_H": 0,
        "fast_fail_exit": False,
        "trailing_exit": False,
        "profit_floor_exit": False,
        "blocked_exit_retry_count": 0,
        "after_cost_return": 0.0,
        "max_adverse_excursion": 0.0,
        "max_favorable_excursion": 0.0,
        "missed_gain_to_exposure": np.nan,
        "turnover": 0.0,
        "strict_capture_50h120": False,
        "partial_capture_50h120": False,
        "exposure_weight_at_first_50pct_target_date": 0.0,
        "selection_eligible": False,
        "selection_status": "no_exposure",
        "price_data_status": "not_simulated",
        "had_exposure": False,
        "fast_failed": False,
        "natural_exited": False,
        "exposure_days": 0,
        "weighted_exposure_days": 0.0,
    }


def _schedule_profile(schedule_id: str, variant_id: str, config: dict[str, Any]) -> dict[str, Any]:
    h = config["holding_rules"]
    w = config["winner_state"]
    profile = {
        "fast_fail_enabled": True,
        "fast_fail_drawdown": float(config["frozen_contract"]["base_fast_fail_drawdown"]),
        "mode": "confirmed",
        "confirmed_h": int(h["unconfirmed_probe_H"]),
        "all_h": None,
        "winner_state": False,
        "winner_gain_threshold": float(w["min_close_return_from_first_exposure"]),
        "winner_trailing": float(w["trailing_drawdown_from_post_winner_high_close"]),
    }
    if schedule_id == "R03_confirmed_H20":
        profile["confirmed_h"] = 20
    elif schedule_id == "R03_confirmed_H60":
        profile["confirmed_h"] = 60
    elif schedule_id == "R03_confirmed_H120":
        profile["confirmed_h"] = 120
    elif schedule_id == "R03_winner_state_hold_H120":
        profile["winner_state"] = True
        profile["confirmed_h"] = int(h["winner_state_normal_hold_H"])
    elif schedule_id == "R03_all_H20":
        profile["mode"] = "all"
        profile["all_h"] = 20
    elif schedule_id == "R03_all_H40":
        profile["mode"] = "all"
        profile["all_h"] = 40
    elif schedule_id == "R03_confirmed_H40":
        profile["confirmed_h"] = 40
    elif schedule_id == "R03_no_fast_fail":
        profile["fast_fail_enabled"] = False
    elif schedule_id == "R03_relaxed_fast_fail":
        profile["fast_fail_drawdown"] = float(config["diagnostic_sensitivity"]["relaxed_fast_fail_drawdown"])
    elif schedule_id == "winner_state_gain_threshold_sensitivity":
        profile["winner_state"] = True
        profile["confirmed_h"] = int(h["winner_state_normal_hold_H"])
        profile["winner_gain_threshold"] = float(variant_id.split("_", 1)[1]) / 100.0
    elif schedule_id == "winner_state_trailing_sensitivity":
        profile["winner_state"] = True
        profile["confirmed_h"] = int(h["winner_state_normal_hold_H"])
        profile["winner_trailing"] = float(variant_id.split("_", 1)[1]) / 100.0
    return profile


def simulate_variant_episode(
    config: dict[str, Any],
    baseline_config: dict[str, Any],
    calendar: pd.DatetimeIndex,
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    universe_set: set[tuple[str, pd.Timestamp]],
    source: pd.Series,
    schedule_id: str,
    variant_id: str,
    role: str,
) -> dict[str, Any]:
    if not _bool(source.get("probe_executed", False)):
        return {"actions": [], "exposures": [], "summary": _empty_summary(source, schedule_id, variant_id, role), "winner_events": []}
    profile = _schedule_profile(schedule_id, variant_id, config)
    instrument = str(source["instrument"]).upper()
    episode_id = str(source["launch_episode_id"])
    probe_exec = _as_date_or_nat(source["selected_probe_execution_date"])
    probe_signal = _as_date_or_nat(source["selected_probe_signal_date"])
    confirm_exec = _as_date_or_nat(source.get("confirm_add_execution_date", ""))
    confirm_signal = _as_date_or_nat(source.get("confirm_add_signal_date", ""))
    confirm_executed_source = _bool(source.get("confirm_add_executed", False)) and not pd.isna(confirm_exec)
    launch_date = _as_date_or_nat(source["launch_effective_date"])
    role = role
    rates = base.cost_rates(baseline_config)
    limit_pct = float(baseline_config["execution"]["limit_inference_pct"]["mainboard_default"])
    exit_retry_until = int(baseline_config["schedule_defaults"]["blocked_exit_retry"]["max_retry_trading_days"])
    max_end_anchor = confirm_exec if confirm_executed_source else probe_exec
    sim_end = base.add_trading_days(calendar, max_end_anchor, 130 + exit_retry_until)
    if pd.isna(sim_end):
        sim_end = calendar[-1]
    sim_dates = calendar[(calendar >= probe_exec) & (calendar <= sim_end)]
    actions: list[dict[str, Any]] = []
    exposures: list[dict[str, Any]] = []
    winner_events: list[dict[str, Any]] = []

    state = "no_exposure"
    actual_weight = 0.0
    target_weight = 0.0
    first_exposure_date = pd.NaT
    first_exposure_price = np.nan
    confirm_add_price = np.nan
    natural_exit_date = pd.NaT
    natural_exit_clock_start = pd.NaT
    natural_exit_h = 0
    exited_date = pd.NaT
    exit_reason = ""
    pending_exit: dict[str, Any] | None = None
    terminal_blocked = False
    total_order_notional = 0.0
    total_cost = 0.0
    cum_gross = 0.0
    cum_net = 0.0
    prev_close = np.nan
    first_close_reference = np.nan
    missed_gain_to_exposure = np.nan
    fast_failed = False
    natural_exited = False
    trailing_exit = False
    profit_floor_exit = False
    probe_executed = False
    confirm_executed = False
    blocked_exit_retry_count = 0
    winner_entered = False
    winner_signal_date = pd.NaT
    winner_effective_date = pd.NaT
    winner_transition_price = np.nan
    pending_winner_effective = pd.NaT
    post_winner_high_close = np.nan
    fast_fail_state_occurred = False

    for date in sim_dates:
        date = pd.Timestamp(date)
        info = lookup.get((instrument, date), {})
        open_price = float(info.get("open", np.nan))
        high_price = float(info.get("high", np.nan))
        low_price = float(info.get("low", np.nan))
        close_price = float(info.get("close", np.nan))
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
            if profile["fast_fail_enabled"] and np.isfinite(low_price) and np.isfinite(first_exposure_price) and low_price / first_exposure_price - 1.0 <= -float(profile["fast_fail_drawdown"]):
                scheduled.append({"action_type": "fast_fail_exit", "target_weight_after": 0.0, "is_exit": True, "retry": False})
            elif winner_entered and np.isfinite(prev_close):
                if np.isfinite(post_winner_high_close) and prev_close / post_winner_high_close - 1.0 <= -float(profile["winner_trailing"]):
                    scheduled.append({"action_type": "trailing_exit", "target_weight_after": 0.0, "is_exit": True, "retry": False})
                elif np.isfinite(first_exposure_price) and prev_close < first_exposure_price * float(config["winner_state"]["profit_floor_from_first_exposure_price"]):
                    scheduled.append({"action_type": "profit_floor_exit", "target_weight_after": 0.0, "is_exit": True, "retry": False})
                elif np.isfinite(confirm_add_price) and prev_close < confirm_add_price:
                    scheduled.append({"action_type": "confirm_add_price_floor_exit", "target_weight_after": 0.0, "is_exit": True, "retry": False})
            if not scheduled and not pd.isna(natural_exit_date) and date >= natural_exit_date:
                scheduled.append({"action_type": "natural_exit", "target_weight_after": 0.0, "is_exit": True, "retry": False})
        if date == probe_exec:
            scheduled.append({"action_type": "probe_entry", "target_weight_after": float(config["frozen_contract"]["probe_weight"]), "is_exit": False, "retry": False})
        if confirm_executed_source and date == confirm_exec and actual_weight > 0 and not fast_failed:
            scheduled.append({"action_type": "confirm_add", "target_weight_after": float(config["frozen_contract"]["full_weight_after_confirm"]), "is_exit": False, "retry": False})
        if profile["winner_state"] and not pd.isna(pending_winner_effective) and date == pending_winner_effective and actual_weight > 0 and not winner_entered:
            scheduled.append({"action_type": "winner_state_enter", "target_weight_after": actual_weight, "is_exit": False, "retry": False})

        for action in sorted(scheduled, key=lambda item: _action_priority(item["action_type"])):
            before_state = state
            before_weight = target_weight
            action_type = action["action_type"]
            desired_weight = float(action["target_weight_after"])
            is_exit = bool(action["is_exit"])
            if action_type == "winner_state_enter":
                winner_entered = True
                winner_effective_date = date
                winner_transition_price = open_price
                state = "winner_hold"
                post_winner_high_close = prev_close if np.isfinite(prev_close) else close_price
                winner_events.append(
                    {
                        "schedule_id": schedule_id,
                        "variant_id": variant_id,
                        "split": source["split"],
                        "launch_episode_id": episode_id,
                        "instrument": instrument,
                        "signal_date": _date_str(winner_signal_date),
                        "effective_date": _date_str(winner_effective_date),
                        "transition_price": winner_transition_price,
                        "close_return_from_first_exposure": np.nan,
                        "max_drawdown_since_first_exposure": np.nan,
                        "close_above_confirm_add_price": True,
                        "fast_fail_state_has_occurred": False,
                        "winner_state_signal_passed": True,
                        "winner_state_entered": True,
                        "feature_max_date": _date_str(winner_signal_date),
                        "asof_passed": True,
                        "no_same_close_transition_passed": winner_effective_date != winner_signal_date,
                    }
                )
                continue
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
                    exited_date = date
                    pending_exit = None
                    exit_reason = action_type
                    natural_exited = action_type == "natural_exit"
                    fast_failed = action_type == "fast_fail_exit"
                    fast_fail_state_occurred = fast_fail_state_occurred or fast_failed
                    trailing_exit = action_type == "trailing_exit"
                    profit_floor_exit = action_type in {"profit_floor_exit", "confirm_add_price_floor_exit"}
                    exit_status = "retry_exit" if action.get("retry") else "normal_exit"
                else:
                    commission = order_notional * rates["commission_buy"]
                    slippage = order_notional * rates["slippage_buy"]
                    target_weight = desired_weight
                    actual_weight = desired_weight
                    if pd.isna(first_exposure_date):
                        first_exposure_date = date
                        first_exposure_price = float(status["execution_price_reference"])
                        first_close_reference = close_price
                        launch_open = float(lookup.get((instrument, launch_date), {}).get("open", np.nan))
                        missed_gain_to_exposure = first_exposure_price / launch_open - 1.0 if np.isfinite(first_exposure_price) and np.isfinite(launch_open) and launch_open > 0 else np.nan
                    if action_type == "confirm_add":
                        confirm_add_price = float(status["execution_price_reference"])
                    probe_executed = probe_executed or action_type == "probe_entry"
                    confirm_executed = confirm_executed or action_type == "confirm_add"
                    if profile["mode"] == "all":
                        natural_exit_clock_start = first_exposure_date
                        natural_exit_h = int(profile["all_h"])
                    elif confirm_executed:
                        natural_exit_clock_start = confirm_exec
                        natural_exit_h = int(profile["confirmed_h"])
                    else:
                        natural_exit_clock_start = probe_exec
                        natural_exit_h = int(config["holding_rules"]["unconfirmed_probe_H"])
                    natural_exit_date = base.add_trading_days(calendar, natural_exit_clock_start, natural_exit_h)
                    state = "full_exposure" if actual_weight >= 0.999 else "partial_exposure"
                action_cost = commission + stamp + slippage
                day_cost += action_cost
                total_cost += action_cost
                total_order_notional += order_notional
            else:
                if is_exit:
                    blocked_exit_retry_count += 1
                    retry_count = pending_exit["retry_count"] + 1 if pending_exit else 1
                    if retry_count > exit_retry_until:
                        terminal_blocked = True
                        terminal_policy = baseline_config["schedule_defaults"]["blocked_exit_retry"]["terminal_price_policy"]
                        state = "exited"
                        target_weight = 0.0
                        actual_weight = 0.0
                        exited_date = date
                        exit_reason = "terminal_blocked_exit"
                        pending_exit = None
                        exit_status = "terminal_blocked_exit"
                    else:
                        pending_exit = {"action_type": action_type, "retry_count": retry_count}
                else:
                    action_type = "blocked_action"
            actions.append(
                {
                    "schedule_id": schedule_id,
                    "variant_id": variant_id,
                    "launch_episode_id": episode_id,
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
                    "variant_id": variant_id,
                    "launch_episode_id": episode_id,
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
        if profile["winner_state"] and confirm_executed and actual_weight > 0 and not winner_entered and pd.isna(pending_winner_effective) and np.isfinite(close_price):
            if np.isfinite(first_exposure_price) and np.isfinite(confirm_add_price) and first_exposure_price > 0:
                since_first = [float(lookup.get((instrument, d), {}).get("low", np.nan)) for d in calendar[(calendar >= first_exposure_date) & (calendar <= date)]]
                finite_lows = [v for v in since_first if np.isfinite(v)]
                max_dd = min(finite_lows) / first_exposure_price - 1.0 if finite_lows else np.nan
                close_ret = close_price / first_exposure_price - 1.0
                passed = (
                    close_ret >= float(profile["winner_gain_threshold"])
                    and np.isfinite(max_dd)
                    and max_dd >= -float(config["winner_state"]["max_drawdown_since_first_exposure"])
                    and close_price > confirm_add_price
                    and not fast_fail_state_occurred
                )
                if passed and date < natural_exit_date:
                    winner_signal_date = date
                    pending_winner_effective = base.next_trading_day(calendar, date)
                    winner_events.append(
                        {
                            "schedule_id": schedule_id,
                            "variant_id": variant_id,
                            "split": source["split"],
                            "launch_episode_id": episode_id,
                            "instrument": instrument,
                            "signal_date": _date_str(winner_signal_date),
                            "effective_date": _date_str(pending_winner_effective),
                            "transition_price": np.nan,
                            "close_return_from_first_exposure": close_ret,
                            "max_drawdown_since_first_exposure": max_dd,
                            "close_above_confirm_add_price": close_price > confirm_add_price,
                            "fast_fail_state_has_occurred": fast_fail_state_occurred,
                            "winner_state_signal_passed": True,
                            "winner_state_entered": False,
                            "feature_max_date": _date_str(date),
                            "asof_passed": True,
                            "no_same_close_transition_passed": pending_winner_effective != date,
                        }
                    )
        if winner_entered and np.isfinite(close_price):
            post_winner_high_close = max(post_winner_high_close, close_price) if np.isfinite(post_winner_high_close) else close_price
        if np.isfinite(close_price):
            prev_close = close_price
        if state == "exited" and pending_exit is None and not pd.isna(exited_date):
            break

    exposure_days = sum(1 for row in exposures if float(row["actual_weight"]) > 0)
    weighted_exposure_days = float(sum(float(row["actual_weight"]) for row in exposures))
    max_adv = float(min([row["cum_return_net"] for row in exposures], default=0.0))
    max_fav = float(max([row["cum_return_net"] for row in exposures], default=0.0))
    summary = _empty_summary(source, schedule_id, variant_id, role)
    summary.update(
        {
            "probe_executed": probe_executed,
            "confirm_add_executed": confirm_executed,
            "winner_state_entered": winner_entered,
            "winner_state_signal_date": _date_str(winner_signal_date),
            "winner_state_effective_date": _date_str(winner_effective_date),
            "winner_state_transition_price": winner_transition_price,
            "first_exposure_date": _date_str(first_exposure_date),
            "first_exposure_price": first_exposure_price,
            "confirm_add_price": confirm_add_price,
            "exit_date": _date_str(exited_date),
            "exit_reason": exit_reason,
            "exit_target_weight_after": 0.0 if not pd.isna(exited_date) else actual_weight,
            "natural_exit_clock_start_date": _date_str(natural_exit_clock_start),
            "natural_exit_H": natural_exit_h,
            "fast_fail_exit": fast_failed,
            "trailing_exit": trailing_exit,
            "profit_floor_exit": profit_floor_exit,
            "blocked_exit_retry_count": blocked_exit_retry_count,
            "after_cost_return": cum_net if not pd.isna(first_exposure_date) else 0.0,
            "max_adverse_excursion": max_adv,
            "max_favorable_excursion": max_fav,
            "missed_gain_to_exposure": missed_gain_to_exposure,
            "turnover": total_order_notional,
            "selection_eligible": role == "primary",
            "selection_status": "selected" if probe_executed else "no_probe",
            "price_data_status": "ok",
            "had_exposure": not pd.isna(first_exposure_date),
            "fast_failed": fast_failed,
            "natural_exited": natural_exited,
            "exposure_days": exposure_days,
            "weighted_exposure_days": weighted_exposure_days,
        }
    )
    return {"actions": actions, "exposures": exposures, "summary": summary, "winner_events": winner_events}


def _augment_r03_baseline(r03_actions: pd.DataFrame, r03_exposures: pd.DataFrame, r03_summaries: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    actions = r03_actions.loc[r03_actions["schedule_id"].eq(R03_PRIMARY)].copy()
    actions["schedule_id"] = BASELINE_SCHEDULE
    actions.insert(1, "variant_id", BASE_VARIANT)
    exposures = r03_exposures.loc[r03_exposures["schedule_id"].eq(R03_PRIMARY)].copy()
    exposures["schedule_id"] = BASELINE_SCHEDULE
    exposures.insert(2, "variant_id", BASE_VARIANT)
    rows = []
    exp_by_ep = {eid: group.copy() for eid, group in exposures.groupby("launch_episode_id", sort=False)}
    for row in r03_summaries.loc[r03_summaries["schedule_id"].eq(R03_PRIMARY)].itertuples(index=False):
        s = pd.Series(row._asdict())
        out = _empty_summary(s, BASELINE_SCHEDULE, BASE_VARIANT, "baseline")
        ep_exp = exp_by_ep.get(str(row.launch_episode_id), pd.DataFrame())
        exposure_days = int(ep_exp["actual_weight"].astype(float).gt(0).sum()) if not ep_exp.empty else 0
        weighted_exposure_days = float(ep_exp["actual_weight"].astype(float).sum()) if not ep_exp.empty else 0.0
        out.update(
            {
                "probe_executed": _bool(row.probe_executed),
                "confirm_add_executed": _bool(row.confirm_add_executed),
                "first_exposure_date": _date_str(row.first_exposure_date),
                "first_exposure_price": float(row.first_exposure_price) if pd.notna(row.first_exposure_price) else np.nan,
                "confirm_add_price": np.nan,
                "exit_date": _date_str(row.exit_date),
                "exit_reason": "fast_fail_exit" if _bool(row.fast_fail_exit) else ("natural_exit" if _bool(row.natural_exit) else ""),
                "natural_exit_clock_start_date": _date_str(row.first_exposure_date),
                "natural_exit_H": 10,
                "fast_fail_exit": _bool(row.fast_fail_exit),
                "natural_exit": _bool(row.natural_exit),
                "after_cost_return": float(row.after_cost_return),
                "missed_gain_to_exposure": float(row.missed_gain_to_exposure) if pd.notna(row.missed_gain_to_exposure) else np.nan,
                "turnover": float(row.turnover),
                "selection_eligible": False,
                "selection_status": "baseline",
                "price_data_status": "r03_inherited",
                "had_exposure": _bool(row.had_exposure),
                "fast_failed": _bool(row.fast_fail_exit),
                "natural_exited": _bool(row.natural_exit),
                "exposure_days": exposure_days,
                "weighted_exposure_days": weighted_exposure_days,
                "max_adverse_excursion": float(ep_exp["cum_return_net"].min()) if not ep_exp.empty else 0.0,
                "max_favorable_excursion": float(ep_exp["cum_return_net"].max()) if not ep_exp.empty else 0.0,
            }
        )
        rows.append(out)
    return actions, exposures, pd.DataFrame(rows)


def apply_capture_metrics(summaries: pd.DataFrame, exposures: pd.DataFrame, targets: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries = summaries.copy()
    targets = targets.copy()
    exp_key = {(row.schedule_id, row.variant_id, row.launch_episode_id, row.date): float(row.actual_weight) for row in exposures.itertuples(index=False)}
    exp_any_before: dict[tuple[str, str, str], set[str]] = {}
    for row in exposures.loc[exposures["actual_weight"].astype(float).gt(0)].itertuples(index=False):
        exp_any_before.setdefault((row.schedule_id, row.variant_id, row.launch_episode_id), set()).add(str(row.date))
    target_by_ep = targets.set_index("launch_episode_id").to_dict("index")
    audit_rows = []
    strict_values = []
    partial_values = []
    weight_values = []
    strict100_values = []
    for row in summaries.itertuples(index=False):
        target = target_by_ep.get(str(row.launch_episode_id), {})
        first50 = target.get("first_50pct_target_date", "")
        first100 = target.get("first_100pct_target_date", "")
        big50 = _bool(target.get("big_winner_50h120", False))
        big100 = _bool(target.get("big_winner_100h240", False))
        weight = 0.0
        weight100 = 0.0
        partial = False
        strict = False
        strict100 = False
        if big50 and first50:
            weight = exp_key.get((row.schedule_id, row.variant_id, row.launch_episode_id, first50), 0.0)
            strict = weight > 0
            dates = exp_any_before.get((row.schedule_id, row.variant_id, row.launch_episode_id), set())
            partial = any(d < first50 for d in dates)
        if big100 and first100:
            weight100 = exp_key.get((row.schedule_id, row.variant_id, row.launch_episode_id, first100), 0.0)
            strict100 = weight100 > 0
        strict_values.append(strict)
        partial_values.append(partial)
        weight_values.append(weight)
        strict100_values.append(strict100)
        audit_rows.append(
            {
                "schedule_id": row.schedule_id,
                "variant_id": row.variant_id,
                "split": row.split,
                "launch_episode_id": row.launch_episode_id,
                "instrument": row.instrument,
                "first_50pct_target_date": first50,
                "first_100pct_target_date": first100,
                "big_winner_50h120": big50,
                "big_winner_100h240": big100,
                "had_positive_exposure_before_first_50pct_target_date": partial,
                "exposure_weight_at_first_50pct_target_date": weight,
                "exposure_weight_at_first_100pct_target_date": weight100,
                "target_day_open_exit_applied": bool(weight == 0 and big50),
                "target_day_capture_timing_status": "open_effective",
                "strict_capture_50h120": strict,
                "strict_capture_100h240": strict100,
                "partial_capture_50h120": partial,
                "exit_date": row.exit_date,
                "exit_before_first_50pct_target": bool(big50 and row.exit_date and row.exit_date < first50),
                "exit_reason": row.exit_reason,
            }
        )
    summaries["strict_capture_50h120"] = strict_values
    summaries["strict_capture_100h240"] = strict100_values
    summaries["partial_capture_50h120"] = partial_values
    summaries["exposure_weight_at_first_50pct_target_date"] = weight_values
    return summaries, pd.DataFrame(audit_rows)


def _instrument_concentration(df: pd.DataFrame) -> tuple[float, float]:
    if df.empty:
        return 0.0, 0.0
    dates = pd.to_datetime(df["first_exposure_date"], errors="coerce")
    keys = df["instrument"].astype(str) + "_" + dates.dt.year.fillna(0).astype(int).astype(str)
    shares = keys.value_counts(normalize=True)
    return float(shares.iloc[0]), float(shares.head(5).sum())


def summarize_results(summaries: pd.DataFrame, baseline_config: dict[str, Any]) -> pd.DataFrame:
    rows = []
    target_counts = summaries.groupby(["schedule_id", "variant_id", "split"], sort=True)
    for (schedule_id, variant_id, split), group in target_counts:
        returns = group["after_cost_return"].astype(float)
        exposure = group["had_exposure"].astype(bool)
        big = group.loc[group["strict_capture_50h120"].notna()]
        big_den = int(group["exposure_weight_at_first_50pct_target_date"].notna().sum())
        big_episode_count = int((group["exposure_weight_at_first_50pct_target_date"].astype(float).ge(0) & group["strict_capture_50h120"].notna()).sum())
        target_episodes = group.loc[group["exposure_weight_at_first_50pct_target_date"].notna()]
        # Count only episodes that actually have a 50h120 target by using audit-compatible nonzero/boolean columns.
        big_target_count = int((target_episodes["strict_capture_50h120"].astype(bool) | target_episodes["partial_capture_50h120"].astype(bool) | target_episodes["exposure_weight_at_first_50pct_target_date"].astype(float).ge(0)).sum())
        top1, top5 = _instrument_concentration(group.loc[exposure])
        role = group["schedule_role"].iloc[0]
        big_mask = group["exposure_weight_at_first_50pct_target_date"].notna()
        # `big_mask` includes all rows; actual denominator is supplied later from audit in schedule-level aggregation.
        bw_count = int(group["strict_capture_50h120"].astype(bool).sum())
        denom = int(group.get("big_winner_50h120", pd.Series(False, index=group.index)).astype(bool).sum()) if "big_winner_50h120" in group else 0
        if denom <= 0:
            denom = int(group["strict_capture_50h120"].astype(bool).sum() + (~group["strict_capture_50h120"].astype(bool) & group["partial_capture_50h120"].astype(bool)).sum())
        exposure_days = group["exposure_days"].astype(float)
        weighted_days = group["weighted_exposure_days"].astype(float)
        rows.append(
            {
                "schedule_id": schedule_id,
                "variant_id": variant_id,
                "schedule_role": role,
                "split": split,
                "episode_count": int(len(group)),
                "episode_with_any_exposure_count": int(exposure.sum()),
                "probe_rate": float(group["probe_executed"].astype(bool).mean()),
                "confirm_add_rate": float(group["confirm_add_executed"].astype(bool).mean()),
                "winner_hold_mode_entry_rate": float(group["winner_state_entered"].astype(bool).mean()),
                "winner_hold_mode_entry_count": int(group["winner_state_entered"].astype(bool).sum()),
                "fast_fail_exit_rate": float(group["fast_fail_exit"].astype(bool).mean()),
                "trailing_exit_rate": float(group["trailing_exit"].astype(bool).mean()),
                "profit_floor_exit_rate": float(group["profit_floor_exit"].astype(bool).mean()),
                "natural_exit_rate": float(group["natural_exited"].astype(bool).mean()),
                "blocked_exit_retry_rate": float(group["blocked_exit_retry_count"].astype(float).gt(0).mean()),
                "mean_after_cost_return": float(returns.mean()),
                "median_after_cost_return": float(returns.median()),
                "p05_after_cost_return": float(returns.quantile(0.05)),
                "p95_after_cost_return": float(returns.quantile(0.95)),
                "max_adverse_excursion_mean": float(group["max_adverse_excursion"].astype(float).mean()),
                "max_adverse_excursion_p95": float(group["max_adverse_excursion"].astype(float).quantile(0.95)),
                "max_favorable_excursion_mean": float(group["max_favorable_excursion"].astype(float).mean()),
                "mean_holding_days": float(exposure_days.loc[exposure].mean()) if exposure.any() else 0.0,
                "median_holding_days": float(exposure_days.loc[exposure].median()) if exposure.any() else 0.0,
                "mean_exposure_days": float(exposure_days.mean()),
                "median_exposure_days": float(exposure_days.median()),
                "capital_occupancy_proxy": float(weighted_days.mean()),
                "turnover_proxy": float(group["turnover"].astype(float).sum() / max(len(group), 1) * 252.0 / max(int(baseline_config["schedule_defaults"]["primary_H"]), 1)),
                "strict_big_winner_capture_rate_50h120": np.nan,
                "exposure_weighted_big_winner_capture_rate_50h120": np.nan,
                "partial_capture_rate_50h120": np.nan,
                "captured_big_winner_count_50h120": bw_count,
                "big_winner_episode_count_50h120": 0,
                "strict_big_winner_capture_rate_100h240_sensitivity": np.nan,
                "top1_instrument_year_exposure_share": top1,
                "top5_instrument_exposure_share": top5,
            }
        )
    return pd.DataFrame(rows)


def fill_capture_rates(results: pd.DataFrame, capture_audit: pd.DataFrame) -> pd.DataFrame:
    results = results.copy()
    for key, group in capture_audit.groupby(["schedule_id", "variant_id", "split"], sort=False):
        sid, vid, split = key
        mask = results["schedule_id"].eq(sid) & results["variant_id"].eq(vid) & results["split"].eq(split)
        big = group.loc[group["big_winner_50h120"].astype(bool)]
        big100 = group.loc[group["big_winner_100h240"].astype(bool)]
        denom = len(big)
        denom100 = len(big100)
        if denom:
            results.loc[mask, "big_winner_episode_count_50h120"] = denom
            results.loc[mask, "captured_big_winner_count_50h120"] = int(big["strict_capture_50h120"].astype(bool).sum())
            results.loc[mask, "strict_big_winner_capture_rate_50h120"] = float(big["strict_capture_50h120"].astype(bool).mean())
            results.loc[mask, "exposure_weighted_big_winner_capture_rate_50h120"] = float(big["exposure_weight_at_first_50pct_target_date"].astype(float).sum() / denom)
            results.loc[mask, "partial_capture_rate_50h120"] = float(big["partial_capture_50h120"].astype(bool).mean())
        else:
            results.loc[mask, ["strict_big_winner_capture_rate_50h120", "exposure_weighted_big_winner_capture_rate_50h120", "partial_capture_rate_50h120"]] = 0.0
        if denom100:
            # Sensitivity uses strict target-day exposure against the 100h240 target date.
            results.loc[mask, "strict_big_winner_capture_rate_100h240_sensitivity"] = float(big100["strict_capture_100h240"].astype(bool).mean())
        else:
            results.loc[mask, "strict_big_winner_capture_rate_100h240_sensitivity"] = 0.0
    return results


def build_comparison(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    baseline = results.loc[results["schedule_id"].eq(BASELINE_SCHEDULE) & results["variant_id"].eq(BASE_VARIANT)].set_index("split")
    for row in results.itertuples(index=False):
        if row.schedule_id == BASELINE_SCHEDULE and row.variant_id == BASE_VARIANT:
            continue
        if row.split not in baseline.index:
            continue
        base_row = baseline.loc[row.split]
        occ_base = float(base_row.capital_occupancy_proxy)
        rows.append(
            {
                "split": row.split,
                "schedule_id": row.schedule_id,
                "variant_id": row.variant_id,
                "comparison_schedule_id": BASELINE_SCHEDULE,
                "schedule_role": row.schedule_role,
                "mean_after_cost_return_diff": float(row.mean_after_cost_return) - float(base_row.mean_after_cost_return),
                "median_after_cost_return_diff": float(row.median_after_cost_return) - float(base_row.median_after_cost_return),
                "p05_after_cost_return_diff": float(row.p05_after_cost_return) - float(base_row.p05_after_cost_return),
                "max_adverse_excursion_mean_diff": float(row.max_adverse_excursion_mean) - float(base_row.max_adverse_excursion_mean),
                "turnover_proxy_diff": float(row.turnover_proxy) - float(base_row.turnover_proxy),
                "turnover_proxy_multiple": float(row.turnover_proxy) / float(base_row.turnover_proxy) if float(base_row.turnover_proxy) else np.inf,
                "exposure_day_multiple_vs_R03": float(row.capital_occupancy_proxy) / occ_base if occ_base else np.inf,
                "capital_occupancy_proxy_diff": float(row.capital_occupancy_proxy) - occ_base,
                "strict_big_winner_capture_rate_50h120_diff": float(row.strict_big_winner_capture_rate_50h120) - float(base_row.strict_big_winner_capture_rate_50h120),
                "exposure_weighted_big_winner_capture_rate_50h120_diff": float(row.exposure_weighted_big_winner_capture_rate_50h120) - float(base_row.exposure_weighted_big_winner_capture_rate_50h120),
                "partial_capture_rate_50h120_diff": float(row.partial_capture_rate_50h120) - float(base_row.partial_capture_rate_50h120),
                "captured_big_winner_count_50h120_diff": int(row.captured_big_winner_count_50h120) - int(base_row.captured_big_winner_count_50h120),
                "winner_hold_mode_entry_rate_diff": float(row.winner_hold_mode_entry_rate) - float(base_row.winner_hold_mode_entry_rate),
                "fast_fail_exit_rate_diff": float(row.fast_fail_exit_rate) - float(base_row.fast_fail_exit_rate),
                "blocked_exit_retry_rate_diff": float(row.blocked_exit_retry_rate) - float(base_row.blocked_exit_retry_rate),
            }
        )
    return pd.DataFrame(rows)


def _passes_validation(row: pd.Series, gate: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons = []
    if float(row.strict_big_winner_capture_rate_50h120_diff) <= float(gate["min_validation_strict_big_winner_capture_diff_vs_R03"]):
        reasons.append("strict_capture_not_improved")
    if int(row.captured_big_winner_count_50h120_diff) < int(gate["min_validation_captured_big_winner_count_delta_vs_R03"]):
        reasons.append("captured_count_not_improved")
    if float(row.exposure_weighted_big_winner_capture_rate_50h120_diff) < float(gate["min_validation_exposure_weighted_capture_diff_vs_R03"]):
        reasons.append("exposure_weighted_capture_deteriorated")
    if float(row.mean_after_cost_return_diff) < float(gate["min_validation_mean_after_cost_return_diff_vs_R03"]):
        reasons.append("mean_return_gate_failed")
    if float(row.p05_after_cost_return_diff) < -float(gate["max_validation_p05_after_cost_return_deterioration_vs_R03"]):
        reasons.append("p05_gate_failed")
    if float(row.max_adverse_excursion_mean_diff) < -float(gate["max_validation_max_adverse_excursion_deterioration_vs_R03"]):
        reasons.append("mae_gate_failed")
    if float(row.turnover_proxy_multiple) > float(gate["max_turnover_proxy_multiple_vs_R03"]):
        reasons.append("turnover_gate_failed")
    if float(row.exposure_day_multiple_vs_R03) > float(gate["max_exposure_day_multiple_vs_R03"]):
        reasons.append("exposure_day_gate_failed")
    return not reasons, reasons


def select_schedule(config: dict[str, Any], results: pd.DataFrame, comparison: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    gate = config["proceed_gate"]
    eligible = set(config["schedule_matrix"]["promotion_eligible_primary_schedule_ids"])
    validation = comparison.loc[comparison["split"].eq("validation") & comparison["schedule_id"].isin(eligible)].copy()
    if validation.empty:
        status = "failed_schedule_extension"
        return pd.DataFrame([_empty_selected(status, config["recommendations"][status])]), status, config["recommendations"][status]
    capture_improvers = validation.loc[
        validation["strict_big_winner_capture_rate_50h120_diff"].astype(float).gt(0)
        & validation["captured_big_winner_count_50h120_diff"].astype(int).ge(int(gate["min_validation_captured_big_winner_count_delta_vs_R03"]))
    ].copy()
    if capture_improvers.empty:
        status = "failed_winner_capture"
        return pd.DataFrame([_empty_selected(status, config["recommendations"][status])]), status, config["recommendations"][status]
    pass_rows = []
    for row in capture_improvers.itertuples(index=False):
        ok, reasons = _passes_validation(pd.Series(row._asdict()), gate)
        res_match = results.loc[
            results["split"].eq("validation") & results["schedule_id"].eq(row.schedule_id) & results["variant_id"].eq(row.variant_id)
        ].iloc[0]
        if row.schedule_id == "R03_winner_state_hold_H120":
            ok = ok and int(res_match.winner_hold_mode_entry_count) >= int(gate["min_winner_state_entry_count_validation"]) and float(res_match.winner_hold_mode_entry_rate) > 0
        if ok:
            pass_rows.append(row._asdict())
    if not pass_rows:
        status = "failed_tail_risk"
        return pd.DataFrame([_empty_selected(status, config["recommendations"][status])]), status, config["recommendations"][status]
    passing = pd.DataFrame(pass_rows)
    passing["_complexity"] = passing["schedule_id"].map({sid: idx for idx, sid in enumerate(COMPLEXITY_ORDER)})
    passing["_blocked_by_materiality"] = False
    for idx, row in passing.iterrows():
        simpler = passing.loc[passing["_complexity"] < row["_complexity"]].copy()
        if simpler.empty:
            continue
        simpler = simpler.sort_values(
            [
                "strict_big_winner_capture_rate_50h120_diff",
                "exposure_weighted_big_winner_capture_rate_50h120_diff",
                "p05_after_cost_return_diff",
                "mean_after_cost_return_diff",
            ],
            ascending=[False, False, False, False],
        )
        best = simpler.iloc[0]
        count_margin = int(row["captured_big_winner_count_50h120_diff"]) - int(best["captured_big_winner_count_50h120_diff"])
        weighted_margin = float(row["exposure_weighted_big_winner_capture_rate_50h120_diff"]) - float(best["exposure_weighted_big_winner_capture_rate_50h120_diff"])
        if count_margin <= int(config["selection_objective"]["materiality_guard"]["strict_capture_count_margin"]) and weighted_margin <= float(config["selection_objective"]["materiality_guard"]["exposure_weighted_capture_margin"]):
            passing.loc[idx, "_blocked_by_materiality"] = True
    remaining = passing.loc[~passing["_blocked_by_materiality"]].copy()
    if remaining.empty:
        status = "failed_schedule_extension"
        return pd.DataFrame([_empty_selected(status, config["recommendations"][status])]), status, config["recommendations"][status]
    selected = remaining.sort_values(
        [
            "strict_big_winner_capture_rate_50h120_diff",
            "exposure_weighted_big_winner_capture_rate_50h120_diff",
            "p05_after_cost_return_diff",
            "mean_after_cost_return_diff",
            "exposure_day_multiple_vs_R03",
            "_complexity",
            "schedule_id",
        ],
        ascending=[False, False, False, False, True, True, True],
    ).iloc[0]
    rob_cmp = comparison.loc[
        comparison["split"].eq("robustness") & comparison["schedule_id"].eq(selected.schedule_id) & comparison["variant_id"].eq(selected.variant_id)
    ]
    robustness_ok = False
    if not rob_cmp.empty:
        r = rob_cmp.iloc[0]
        robustness_ok = (
            float(r.strict_big_winner_capture_rate_50h120_diff) >= float(gate["min_robustness_strict_big_winner_capture_diff_vs_R03"])
            and float(r.exposure_weighted_big_winner_capture_rate_50h120_diff) >= float(gate["min_robustness_exposure_weighted_capture_diff_vs_R03"])
            and float(r.mean_after_cost_return_diff) >= float(gate["min_robustness_mean_after_cost_return_diff_vs_R03"])
            and float(r.p05_after_cost_return_diff) >= -float(gate["max_robustness_p05_after_cost_return_deterioration_vs_R03"])
            and float(r.max_adverse_excursion_mean_diff) >= -float(gate["max_robustness_max_adverse_excursion_deterioration_vs_R03"])
            and float(r.turnover_proxy_multiple) <= float(gate["max_turnover_proxy_multiple_vs_R03"])
            and float(r.exposure_day_multiple_vs_R03) <= float(gate["max_exposure_day_multiple_vs_R03"])
        )
        rob_res = results.loc[
            results["split"].eq("robustness") & results["schedule_id"].eq(selected.schedule_id) & results["variant_id"].eq(selected.variant_id)
        ]
        if selected.schedule_id == "R03_winner_state_hold_H120" and not rob_res.empty:
            robustness_ok = robustness_ok and int(rob_res.iloc[0].winner_hold_mode_entry_count) >= int(gate["min_winner_state_entry_count_robustness"]) and float(rob_res.iloc[0].winner_hold_mode_entry_rate) > 0
    status = "passed" if robustness_ok else "failed_robustness_holdout"
    selected_row = {
        "selected_schedule_id": selected.schedule_id,
        "selected_variant_id": selected.variant_id,
        "selection_split": "validation",
        "selection_status": status,
        "selected_from_primary_matrix": True,
        "validation_objective_rank": 1,
        "validation_strict_big_winner_capture_rate_50h120_diff_vs_R03": selected.strict_big_winner_capture_rate_50h120_diff,
        "validation_exposure_weighted_big_winner_capture_rate_50h120_diff_vs_R03": selected.exposure_weighted_big_winner_capture_rate_50h120_diff,
        "validation_p05_after_cost_return_diff_vs_R03": selected.p05_after_cost_return_diff,
        "validation_mean_after_cost_return_diff_vs_R03": selected.mean_after_cost_return_diff,
        "validation_exposure_day_multiple_vs_R03": selected.exposure_day_multiple_vs_R03,
        "materiality_guard_applied": bool(passing["_blocked_by_materiality"].any()),
        "winner_state_min_support_pass": True,
        "robustness_gate_status": "passed" if robustness_ok else "failed",
        "next_phase_proceed_status": status,
        "recommendation": config["recommendations"][status],
    }
    return pd.DataFrame([selected_row]), status, selected_row["recommendation"]


def _empty_selected(status: str, recommendation: str = "") -> dict[str, Any]:
    return {
        "selected_schedule_id": "",
        "selected_variant_id": "",
        "selection_split": "validation",
        "selection_status": status,
        "selected_from_primary_matrix": False,
        "validation_objective_rank": 0,
        "validation_strict_big_winner_capture_rate_50h120_diff_vs_R03": np.nan,
        "validation_exposure_weighted_big_winner_capture_rate_50h120_diff_vs_R03": np.nan,
        "validation_p05_after_cost_return_diff_vs_R03": np.nan,
        "validation_mean_after_cost_return_diff_vs_R03": np.nan,
        "validation_exposure_day_multiple_vs_R03": np.nan,
        "materiality_guard_applied": False,
        "winner_state_min_support_pass": False,
        "robustness_gate_status": "not_evaluated",
        "next_phase_proceed_status": status,
        "recommendation": recommendation,
    }


def build_gate_audit(
    config: dict[str, Any],
    selected: pd.DataFrame,
    comparison: pd.DataFrame,
    results: pd.DataFrame,
    r03_reconciliation: list[dict[str, Any]],
    asof: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add(split: str, schedule_id: str, variant_id: str, name: str, value: Any, threshold: Any, passed: bool, category: str, hard: bool = True) -> None:
        rows.append(
            {
                "split": split,
                "schedule_id": schedule_id,
                "variant_id": variant_id,
                "gate_name": name,
                "gate_value": value,
                "gate_threshold": threshold,
                "passed": bool(passed),
                "failure_reason": "" if passed else "gate_failed",
                "is_hard_stop": bool(hard),
                "failure_category": category,
            }
        )

    for item in r03_reconciliation:
        is_required_split = item["split"] in {"validation", "robustness"}
        add(item["split"], BASELINE_SCHEDULE, BASE_VARIANT, item["gate_name"], item["value"], item["threshold"], item["passed"], "contract_or_leakage", hard=is_required_split)
    add("all", BASELINE_SCHEDULE, BASE_VARIANT, "baseline_schedule_not_promotion_eligible", False, False, True, "contract_or_leakage")
    add("all", "diagnostic", "", "diagnostic_not_promotion_eligible", False, False, True, "contract_or_leakage")
    selected_row = selected.iloc[0]
    if not selected_row.get("selected_schedule_id", ""):
        eligible = set(config["schedule_matrix"]["promotion_eligible_primary_schedule_ids"])
        gate = config["proceed_gate"]
        candidates = comparison.loc[comparison["split"].eq("validation") & comparison["schedule_id"].isin(eligible)].copy()
        for cmp_row in candidates.itertuples(index=False):
            res = results.loc[
                results["split"].eq("validation")
                & results["schedule_id"].eq(cmp_row.schedule_id)
                & results["variant_id"].eq(cmp_row.variant_id)
            ]
            add("validation", cmp_row.schedule_id, cmp_row.variant_id, "candidate_strict_capture_diff", cmp_row.strict_big_winner_capture_rate_50h120_diff, "> 0", float(cmp_row.strict_big_winner_capture_rate_50h120_diff) > 0.0, "winner_capture")
            add("validation", cmp_row.schedule_id, cmp_row.variant_id, "candidate_captured_big_winner_count_delta", cmp_row.captured_big_winner_count_50h120_diff, gate["min_validation_captured_big_winner_count_delta_vs_R03"], int(cmp_row.captured_big_winner_count_50h120_diff) >= int(gate["min_validation_captured_big_winner_count_delta_vs_R03"]), "winner_capture")
            add("validation", cmp_row.schedule_id, cmp_row.variant_id, "candidate_exposure_weighted_capture_diff", cmp_row.exposure_weighted_big_winner_capture_rate_50h120_diff, gate["min_validation_exposure_weighted_capture_diff_vs_R03"], float(cmp_row.exposure_weighted_big_winner_capture_rate_50h120_diff) >= float(gate["min_validation_exposure_weighted_capture_diff_vs_R03"]), "winner_capture")
            add("validation", cmp_row.schedule_id, cmp_row.variant_id, "candidate_mean_return_diff", cmp_row.mean_after_cost_return_diff, gate["min_validation_mean_after_cost_return_diff_vs_R03"], float(cmp_row.mean_after_cost_return_diff) >= float(gate["min_validation_mean_after_cost_return_diff_vs_R03"]), "tail_risk")
            add("validation", cmp_row.schedule_id, cmp_row.variant_id, "candidate_p05_return_diff", cmp_row.p05_after_cost_return_diff, -float(gate["max_validation_p05_after_cost_return_deterioration_vs_R03"]), float(cmp_row.p05_after_cost_return_diff) >= -float(gate["max_validation_p05_after_cost_return_deterioration_vs_R03"]), "tail_risk")
            add("validation", cmp_row.schedule_id, cmp_row.variant_id, "candidate_mae_mean_diff", cmp_row.max_adverse_excursion_mean_diff, -float(gate["max_validation_max_adverse_excursion_deterioration_vs_R03"]), float(cmp_row.max_adverse_excursion_mean_diff) >= -float(gate["max_validation_max_adverse_excursion_deterioration_vs_R03"]), "tail_risk")
            add("validation", cmp_row.schedule_id, cmp_row.variant_id, "candidate_turnover_proxy_multiple", cmp_row.turnover_proxy_multiple, gate["max_turnover_proxy_multiple_vs_R03"], float(cmp_row.turnover_proxy_multiple) <= float(gate["max_turnover_proxy_multiple_vs_R03"]), "tail_risk")
            add("validation", cmp_row.schedule_id, cmp_row.variant_id, "candidate_exposure_day_multiple", cmp_row.exposure_day_multiple_vs_R03, gate["max_exposure_day_multiple_vs_R03"], float(cmp_row.exposure_day_multiple_vs_R03) <= float(gate["max_exposure_day_multiple_vs_R03"]), "tail_risk")
            if not res.empty:
                res_row = res.iloc[0]
                add("validation", cmp_row.schedule_id, cmp_row.variant_id, "candidate_blocked_exit_retry_rate", res_row.blocked_exit_retry_rate, gate["max_blocked_exit_retry_rate"], float(res_row.blocked_exit_retry_rate) <= float(gate["max_blocked_exit_retry_rate"]), "tail_risk")
                add("validation", cmp_row.schedule_id, cmp_row.variant_id, "candidate_top1_instrument_year_exposure_share", res_row.top1_instrument_year_exposure_share, gate["max_top1_instrument_year_exposure_share"], float(res_row.top1_instrument_year_exposure_share) <= float(gate["max_top1_instrument_year_exposure_share"]), "tail_risk")
                add("validation", cmp_row.schedule_id, cmp_row.variant_id, "candidate_top5_instrument_exposure_share", res_row.top5_instrument_exposure_share, gate["max_top5_instrument_exposure_share"], float(res_row.top5_instrument_exposure_share) <= float(gate["max_top5_instrument_exposure_share"]), "tail_risk")
                if cmp_row.schedule_id == "R03_winner_state_hold_H120":
                    add(
                        "validation",
                        cmp_row.schedule_id,
                        cmp_row.variant_id,
                        "candidate_winner_state_min_support_pass",
                        res_row.winner_hold_mode_entry_count,
                        gate["min_winner_state_entry_count_validation"],
                        int(res_row.winner_hold_mode_entry_count) >= int(gate["min_winner_state_entry_count_validation"]) and float(res_row.winner_hold_mode_entry_rate) > 0,
                        "tail_risk",
                    )
    else:
        sid = selected_row.selected_schedule_id
        vid = selected_row.selected_variant_id
        for split in ["validation", "robustness"]:
            cmp = comparison.loc[comparison["split"].eq(split) & comparison["schedule_id"].eq(sid) & comparison["variant_id"].eq(vid)]
            res = results.loc[results["split"].eq(split) & results["schedule_id"].eq(sid) & results["variant_id"].eq(vid)]
            if cmp.empty or res.empty:
                add(split, sid, vid, "selected_split_present", False, True, False, "contract_or_leakage")
                continue
            cmp_row = cmp.iloc[0]
            res_row = res.iloc[0]
            gate = config["proceed_gate"]
            add(split, sid, vid, "strict_capture_diff", cmp_row.strict_big_winner_capture_rate_50h120_diff, 0.0, float(cmp_row.strict_big_winner_capture_rate_50h120_diff) >= (0.0 if split == "robustness" else np.nextafter(0, 1)), "winner_capture")
            add(split, sid, vid, "exposure_weighted_capture_non_deterioration", cmp_row.exposure_weighted_big_winner_capture_rate_50h120_diff, 0.0, float(cmp_row.exposure_weighted_big_winner_capture_rate_50h120_diff) >= 0.0, "winner_capture")
            add(split, sid, vid, "mean_return_diff", cmp_row.mean_after_cost_return_diff, gate["min_validation_mean_after_cost_return_diff_vs_R03"] if split == "validation" else gate["min_robustness_mean_after_cost_return_diff_vs_R03"], float(cmp_row.mean_after_cost_return_diff) >= float(gate["min_validation_mean_after_cost_return_diff_vs_R03"] if split == "validation" else gate["min_robustness_mean_after_cost_return_diff_vs_R03"]), "tail_risk")
            add(split, sid, vid, "p05_return_diff", cmp_row.p05_after_cost_return_diff, -float(gate["max_validation_p05_after_cost_return_deterioration_vs_R03"] if split == "validation" else gate["max_robustness_p05_after_cost_return_deterioration_vs_R03"]), float(cmp_row.p05_after_cost_return_diff) >= -float(gate["max_validation_p05_after_cost_return_deterioration_vs_R03"] if split == "validation" else gate["max_robustness_p05_after_cost_return_deterioration_vs_R03"]), "tail_risk")
            add(split, sid, vid, "exposure_day_multiple_gate", cmp_row.exposure_day_multiple_vs_R03, gate["max_exposure_day_multiple_vs_R03"], float(cmp_row.exposure_day_multiple_vs_R03) <= float(gate["max_exposure_day_multiple_vs_R03"]), "tail_risk")
            add(split, sid, vid, "turnover_proxy_multiple", cmp_row.turnover_proxy_multiple, gate["max_turnover_proxy_multiple_vs_R03"], float(cmp_row.turnover_proxy_multiple) <= float(gate["max_turnover_proxy_multiple_vs_R03"]), "tail_risk")
            add(split, sid, vid, "top1_instrument_year_exposure_share", res_row.top1_instrument_year_exposure_share, gate["max_top1_instrument_year_exposure_share"], float(res_row.top1_instrument_year_exposure_share) <= float(gate["max_top1_instrument_year_exposure_share"]), "tail_risk")
            add(split, sid, vid, "top5_instrument_exposure_share", res_row.top5_instrument_exposure_share, gate["max_top5_instrument_exposure_share"], float(res_row.top5_instrument_exposure_share) <= float(gate["max_top5_instrument_exposure_share"]), "tail_risk")
            if sid == "R03_winner_state_hold_H120":
                min_count = gate["min_winner_state_entry_count_validation"] if split == "validation" else gate["min_winner_state_entry_count_robustness"]
                add(split, sid, vid, "winner_state_min_support_pass", res_row.winner_hold_mode_entry_count, min_count, int(res_row.winner_hold_mode_entry_count) >= int(min_count) and float(res_row.winner_hold_mode_entry_rate) > 0, "tail_risk")
    add("all", selected_row.get("selected_schedule_id", ""), selected_row.get("selected_variant_id", ""), "selection_materiality_guard_applied", selected_row.get("materiality_guard_applied", False), "reported", True, "selection", hard=False)
    if not asof.empty:
        add("all", "winner_state", "", "winner_state_asof_audit_pass", bool(asof["asof_passed"].astype(bool).all()), True, bool(asof["asof_passed"].astype(bool).all()), "contract_or_leakage")
    return pd.DataFrame(rows)


def build_fast_fail_audit(config: dict[str, Any], summaries: pd.DataFrame) -> pd.DataFrame:
    rows = []
    threshold = float(config["diagnostic_sensitivity"]["fast_fail_saved_loss_threshold"])
    pairs = [((BASELINE_SCHEDULE, BASE_VARIANT), ("R03_no_fast_fail", "no_fast_fail")), ((BASELINE_SCHEDULE, BASE_VARIANT), ("R03_relaxed_fast_fail", "relaxed_fast_fail"))]
    for (base_key, cf_key) in pairs:
        base_df = summaries.loc[summaries["schedule_id"].eq(base_key[0]) & summaries["variant_id"].eq(base_key[1])].set_index(["split", "launch_episode_id"])
        cf_df = summaries.loc[summaries["schedule_id"].eq(cf_key[0]) & summaries["variant_id"].eq(cf_key[1])].set_index(["split", "launch_episode_id"])
        for split in sorted(set(base_df.index.get_level_values(0)) & set(cf_df.index.get_level_values(0))):
            saved = false_winner = false_big = false_partial = 0
            b_split = base_df.loc[split]
            c_split = cf_df.loc[split]
            common = b_split.index.intersection(c_split.index)
            b_common = b_split.loc[common]
            c_common = c_split.loc[common]
            mean_delta = float(c_common["after_cost_return"].astype(float).mean() - b_common["after_cost_return"].astype(float).mean()) if len(common) else np.nan
            p05_delta = float(c_common["after_cost_return"].astype(float).quantile(0.05) - b_common["after_cost_return"].astype(float).quantile(0.05)) if len(common) else np.nan
            mae_delta = float(c_common["max_adverse_excursion"].astype(float).mean() - b_common["max_adverse_excursion"].astype(float).mean()) if len(common) else np.nan
            b_big = b_common.loc[b_common["big_winner_50h120"].astype(bool)] if "big_winner_50h120" in b_common else b_common.iloc[0:0]
            c_big = c_common.loc[c_common["big_winner_50h120"].astype(bool)] if "big_winner_50h120" in c_common else c_common.iloc[0:0]
            if len(b_big) and len(c_big):
                capture_delta = float(c_big["strict_capture_50h120"].astype(bool).mean() - b_big["strict_capture_50h120"].astype(bool).mean())
                weighted_delta = float(c_big["exposure_weight_at_first_50pct_target_date"].astype(float).sum() / len(c_big) - b_big["exposure_weight_at_first_50pct_target_date"].astype(float).sum() / len(b_big))
                partial_delta = float(c_big["partial_capture_50h120"].astype(bool).mean() - b_big["partial_capture_50h120"].astype(bool).mean())
            else:
                capture_delta = weighted_delta = partial_delta = 0.0
            for eid in common:
                b = b_split.loc[eid]
                c = c_split.loc[eid]
                if _bool(b.fast_fail_exit) and float(c.after_cost_return) - float(b.after_cost_return) <= -threshold:
                    saved += 1
                if _bool(b.fast_fail_exit) and _bool(c.strict_capture_50h120):
                    false_winner += 1
                if _bool(b.fast_fail_exit) and _bool(c.strict_capture_50h120):
                    false_big += 1
                if _bool(b.fast_fail_exit) and _bool(c.partial_capture_50h120):
                    false_partial += 1
            rows.append(
                {
                    "schedule_id": base_key[0],
                    "variant_id": base_key[1],
                    "counterfactual_id": cf_key[0],
                    "counterfactual_variant_id": cf_key[1],
                    "split": split,
                    "big_winner_capture_delta": capture_delta,
                    "exposure_weighted_capture_delta": weighted_delta,
                    "partial_capture_delta": partial_delta,
                    "mean_return_delta": mean_delta,
                    "p05_return_delta": p05_delta,
                    "max_adverse_excursion_delta": mae_delta,
                    "fast_fail_saved_loss_count": saved,
                    "fast_fail_false_exit_winner_count": false_winner,
                    "fast_fail_false_exit_big_winner_count": false_big,
                    "fast_fail_false_exit_partial_capture_count": false_partial,
                }
            )
    return pd.DataFrame(rows)


def build_artifacts(config: dict[str, Any], paths: RequirementPaths, baseline_config: dict[str, Any], baseline_paths: base.Paths) -> dict[str, Any]:
    r03_actions = pd.read_parquet(paths.requirement_03_output_root / "cache" / "requirement_03_schedule_action_panel.parquet")
    r03_exposures = pd.read_parquet(paths.requirement_03_output_root / "cache" / "requirement_03_exposure_daily_panel.parquet")
    r03_summaries = pd.read_parquet(paths.requirement_03_output_root / "cache" / "requirement_03_episode_schedule_summary.parquet")
    r03_results = pd.read_csv(paths.requirement_03_output_root / "reports" / "requirement_03_schedule_results.csv")
    episodes = r03_summaries.loc[r03_summaries["schedule_id"].eq(R03_PRIMARY)].copy()
    panel = base.load_market_panel(baseline_config)
    lookup = base.price_lookup(panel)
    universe_set = base.universe_membership_set(baseline_config)
    calendar = base.load_calendar(baseline_config)
    price_authority = compute_price_authority(config, baseline_config, episodes, panel, calendar)
    targets = build_big_winner_targets(baseline_config, lookup, calendar, episodes)
    base_actions, base_exposures, base_summaries = _augment_r03_baseline(r03_actions, r03_exposures, r03_summaries)
    action_rows = base_actions.to_dict("records")
    exposure_rows = base_exposures.to_dict("records")
    summary_rows = base_summaries.to_dict("records")
    winner_rows: list[dict[str, Any]] = []
    catalog = _variant_catalog(config)
    for variant in catalog:
        sid = variant["schedule_id"]
        if sid == BASELINE_SCHEDULE:
            continue
        for ep in episodes.itertuples(index=False):
            source = pd.Series(ep._asdict())
            result = simulate_variant_episode(config, baseline_config, calendar, lookup, universe_set, source, sid, variant["variant_id"], variant["schedule_role"])
            action_rows.extend(result["actions"])
            exposure_rows.extend(result["exposures"])
            summary_rows.append(result["summary"])
            winner_rows.extend(result["winner_events"])
    actions = pd.DataFrame(action_rows)
    exposures = pd.DataFrame(exposure_rows)
    summaries = pd.DataFrame(summary_rows)
    summaries, capture_audit = apply_capture_metrics(summaries, exposures, targets)
    summaries = summaries.merge(targets[["launch_episode_id", "big_winner_50h120", "big_winner_100h240"]], on="launch_episode_id", how="left")
    results = fill_capture_rates(summarize_results(summaries, baseline_config), capture_audit)
    comparison = build_comparison(results)
    selected, status, recommendation = select_schedule(config, results, comparison)
    asof = pd.DataFrame(winner_rows)
    if asof.empty:
        asof = pd.DataFrame(columns=["schedule_id", "variant_id", "split", "launch_episode_id", "instrument", "winner_state_signal_date", "winner_state_effective_date", "winner_state_feature_max_date", "winner_state_transition_price_date", "same_close_transition_used", "effective_date_high_low_close_used_as_signal", "future_target_label_used_as_signal", "asof_passed", "detail"])
    else:
        asof = asof.rename(columns={"signal_date": "winner_state_signal_date", "effective_date": "winner_state_effective_date", "feature_max_date": "winner_state_feature_max_date"})
        asof["winner_state_transition_price_date"] = asof["winner_state_effective_date"]
        asof["same_close_transition_used"] = asof["winner_state_signal_date"].eq(asof["winner_state_effective_date"])
        asof["effective_date_high_low_close_used_as_signal"] = False
        asof["future_target_label_used_as_signal"] = False
        asof["detail"] = ""
    r03_reconciliation = baseline_reconciliation(results, r03_results)
    gate_audit = build_gate_audit(config, selected, comparison, results, r03_reconciliation, asof)
    fast_fail = build_fast_fail_audit(config, summaries)
    diagnostics = build_diagnostic_counterfactuals(results, comparison)
    return {
        "actions": actions,
        "exposures": exposures,
        "summaries": summaries,
        "winner_state": pd.DataFrame(winner_rows),
        "results": results,
        "comparison": comparison,
        "selected": selected,
        "capture_audit": capture_audit,
        "fast_fail": fast_fail,
        "asof": asof,
        "diagnostics": diagnostics,
        "gate_audit": gate_audit,
        "status": status,
        "recommendation": recommendation,
        "price_authority": price_authority,
    }


def baseline_reconciliation(results: pd.DataFrame, r03_results: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    base_res = results.loc[results["schedule_id"].eq(BASELINE_SCHEDULE) & results["variant_id"].eq(BASE_VARIANT)].set_index("split")
    r03 = r03_results.loc[r03_results["schedule_id"].eq(R03_PRIMARY)].set_index("split")
    checks = [
        ("r03_replay_episode_count_match", "episode_count", 0.0),
        ("r03_replay_exposed_count_match", "episode_with_any_exposure_count", 0.0),
        ("r03_replay_probe_rate_match", "probe_rate", 1e-12),
        ("r03_replay_confirm_add_rate_match", "confirm_add_rate", 1e-12),
        ("r03_replay_mean_after_cost_return_match", "mean_after_cost_return", 1e-10),
        ("r03_replay_p05_after_cost_return_match", "p05_after_cost_return", 1e-10),
        ("r03_replay_strict_big_winner_capture_match", "strict_big_winner_capture_rate_50h120", 1e-12),
    ]
    for split in sorted(set(base_res.index) & set(r03.index)):
        for gate_name, col, tol in checks:
            r04_col = "strict_big_winner_capture_rate_50h120" if col == "strict_big_winner_capture_rate_50h120" else col
            r03_col = "big_winner_capture_rate" if col == "strict_big_winner_capture_rate_50h120" else col
            value = float(base_res.loc[split, r04_col])
            threshold = float(r03.loc[split, r03_col])
            passed = abs(value - threshold) <= tol
            rows.append({"split": split, "gate_name": gate_name, "value": value, "threshold": threshold, "passed": passed})
    return rows


def build_diagnostic_counterfactuals(results: pd.DataFrame, comparison: pd.DataFrame) -> pd.DataFrame:
    rows = []
    diag = results.loc[results["schedule_role"].eq("diagnostic")]
    for row in diag.itertuples(index=False):
        for metric in ["mean_after_cost_return", "p05_after_cost_return", "strict_big_winner_capture_rate_50h120", "exposure_weighted_big_winner_capture_rate_50h120", "partial_capture_rate_50h120"]:
            cmp = comparison.loc[
                comparison["schedule_id"].eq(row.schedule_id) & comparison["variant_id"].eq(row.variant_id) & comparison["split"].eq(row.split)
            ]
            diff = np.nan
            diff_col = {
                "mean_after_cost_return": "mean_after_cost_return_diff",
                "p05_after_cost_return": "p05_after_cost_return_diff",
                "strict_big_winner_capture_rate_50h120": "strict_big_winner_capture_rate_50h120_diff",
                "exposure_weighted_big_winner_capture_rate_50h120": "exposure_weighted_big_winner_capture_rate_50h120_diff",
                "partial_capture_rate_50h120": "partial_capture_rate_50h120_diff",
            }[metric]
            if not cmp.empty:
                diff = cmp.iloc[0][diff_col]
            rows.append(
                {
                    "schedule_id": row.schedule_id,
                    "variant_id": row.variant_id,
                    "diagnostic_family": row.schedule_id,
                    "parameter_name": "",
                    "parameter_value": np.nan,
                    "split": row.split,
                    "metric_name": metric,
                    "metric_value": getattr(row, metric),
                    "diff_vs_R03": diff,
                    "eligible_for_selection": False,
                    "diagnostic_interpretation": "diagnostic_only",
                }
            )
    return pd.DataFrame(rows)


def _authority_row(name: str, path: Path, role: str, producer: str) -> dict[str, Any]:
    if path.suffix == ".csv" and path.exists():
        row_count = len(pd.read_csv(path))
    elif path.suffix == ".parquet" and path.exists():
        row_count = len(pd.read_parquet(path))
    elif path.exists():
        row_count = 1
    else:
        row_count = 0
    return {
        "artifact_name": name,
        "artifact_path": relpath(path),
        "authority_role": role,
        "producer_command": producer,
        "schema_version": SCHEMA_VERSION,
        "required_for_requirement": True,
        "row_count": int(row_count),
        "content_hash": file_hash(path) if path.exists() else "",
    }


def write_artifact_authority(paths: RequirementPaths) -> pd.DataFrame:
    producer = "uv run python ep2/scripts/run_requirement_04_holding_exit_winner_capture_extension.py --config ep2/configs/requirement_04_holding_exit_winner_capture_extension.yaml"
    rows = []
    for name in REQUIRED_CACHE:
        rows.append(_authority_row(name, paths.cache_dir / name, "cache", producer))
    for name in REQUIRED_REPORTS:
        if name != "requirement_04_artifact_authority.csv":
            rows.append(_authority_row(name, paths.reports_dir / name, "report", producer))
    for name in REQUIRED_MANIFESTS:
        rows.append(_authority_row(name, paths.manifests_dir / name, "manifest", producer))
    authority = pd.DataFrame(rows)
    write_csv(authority, paths.reports_dir / "requirement_04_artifact_authority.csv")
    return authority


def _columns_with_variant(df: pd.DataFrame, base_columns: list[str], include_variant_after: str) -> pd.DataFrame:
    cols = list(base_columns)
    if "variant_id" not in cols:
        pos = cols.index(include_variant_after) + 1
        cols.insert(pos, "variant_id")
    for col in cols:
        if col not in df:
            df[col] = np.nan
    extra = [c for c in df.columns if c not in cols]
    return df[cols + extra]


def run_requirement_04(config_path: str | Path) -> dict[str, Any]:
    config, paths, baseline_config, baseline_paths = load_requirement_config(config_path)
    r03_state = assert_requirement_03_entry(config)
    artifacts = build_artifacts(config, paths, baseline_config, baseline_paths)
    actions = _columns_with_variant(artifacts["actions"], base.action_columns(), "schedule_id")
    exposures = _columns_with_variant(artifacts["exposures"], base.exposure_columns(), "schedule_id")
    write_parquet(actions, paths.cache_dir / "requirement_04_schedule_action_panel.parquet")
    write_parquet(exposures, paths.cache_dir / "requirement_04_exposure_daily_panel.parquet")
    write_parquet(artifacts["summaries"], paths.cache_dir / "requirement_04_episode_schedule_summary.parquet")
    write_parquet(artifacts["winner_state"], paths.cache_dir / "requirement_04_winner_state_event_panel.parquet")
    write_csv(artifacts["results"], paths.reports_dir / "requirement_04_schedule_results.csv")
    write_csv(artifacts["comparison"], paths.reports_dir / "requirement_04_schedule_comparison.csv")
    write_csv(artifacts["selected"], paths.reports_dir / "requirement_04_selected_schedule.csv")
    write_csv(artifacts["capture_audit"], paths.reports_dir / "requirement_04_big_winner_capture_audit.csv")
    write_csv(artifacts["fast_fail"], paths.reports_dir / "requirement_04_fast_fail_value_audit.csv")
    write_csv(artifacts["asof"], paths.reports_dir / "requirement_04_winner_state_asof_audit.csv")
    write_csv(artifacts["diagnostics"], paths.reports_dir / "requirement_04_diagnostic_counterfactuals.csv")
    write_csv(artifacts["gate_audit"], paths.reports_dir / "requirement_04_gate_audit.csv")
    manifest = {
        "phase": config["phase"],
        "validation_status": artifacts["status"],
        "next_phase_proceed_status": artifacts["status"],
        "recommendation": artifacts["recommendation"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requirement_03_manifest_hash": r03_state["manifest_hash"],
        "requirement_02_manifest_hash": r03_state["manifest"].get("requirement_02_manifest_hash", ""),
        "engineering_baseline_manifest_hash": file_hash(paths.baseline_output_root / "manifests" / "ep2_engineering_baseline_manifest.json"),
        **artifacts["price_authority"],
        "primary_label_id": config["frozen_contract"]["primary_label_id"],
        "frozen_baseline_id": config["frozen_contract"]["frozen_baseline_id"],
        "hazard_schedule_id": config["frozen_contract"]["hazard_schedule_id"],
        "schedule_bridge_id": config["frozen_contract"]["schedule_bridge_id"],
        "selected_threshold": config["frozen_contract"]["selected_threshold"],
        "selected_stop_risk_ceiling": config["frozen_contract"]["selected_stop_risk_ceiling"],
        "selected_requirement_04_schedule_id": artifacts["selected"].iloc[0].get("selected_schedule_id", ""),
        "selected_schedule_role": "primary" if artifacts["selected"].iloc[0].get("selected_schedule_id", "") else "",
        "winner_state_enabled": artifacts["selected"].iloc[0].get("selected_schedule_id", "") == "R03_winner_state_hold_H120",
        "schedule_action_panel_hash": file_hash(paths.cache_dir / "requirement_04_schedule_action_panel.parquet"),
        "exposure_daily_panel_hash": file_hash(paths.cache_dir / "requirement_04_exposure_daily_panel.parquet"),
        "episode_schedule_summary_hash": file_hash(paths.cache_dir / "requirement_04_episode_schedule_summary.parquet"),
        "winner_state_event_panel_hash": file_hash(paths.cache_dir / "requirement_04_winner_state_event_panel.parquet"),
        "schedule_results_hash": file_hash(paths.reports_dir / "requirement_04_schedule_results.csv"),
        "schedule_comparison_hash": file_hash(paths.reports_dir / "requirement_04_schedule_comparison.csv"),
        "selected_schedule_hash": file_hash(paths.reports_dir / "requirement_04_selected_schedule.csv"),
        "big_winner_capture_audit_hash": file_hash(paths.reports_dir / "requirement_04_big_winner_capture_audit.csv"),
        "fast_fail_value_audit_hash": file_hash(paths.reports_dir / "requirement_04_fast_fail_value_audit.csv"),
        "winner_state_asof_audit_hash": file_hash(paths.reports_dir / "requirement_04_winner_state_asof_audit.csv"),
        "diagnostic_counterfactuals_hash": file_hash(paths.reports_dir / "requirement_04_diagnostic_counterfactuals.csv"),
        "gate_audit_hash": file_hash(paths.reports_dir / "requirement_04_gate_audit.csv"),
    }
    write_json(manifest, paths.manifests_dir / "requirement_04_holding_exit_manifest.json")
    authority = write_artifact_authority(paths)
    manifest["artifact_authority_hash"] = file_hash(paths.reports_dir / "requirement_04_artifact_authority.csv")
    write_json(manifest, paths.manifests_dir / "requirement_04_holding_exit_manifest.json")
    return {
        "validation_status": artifacts["status"],
        "next_phase_proceed_status": artifacts["status"],
        "recommendation": artifacts["recommendation"],
        "selected_schedule_id": manifest["selected_requirement_04_schedule_id"],
        "artifact_count": int(len(authority) + 1),
    }


def validate_requirement_04(config_path: str | Path, fail_on_gate_status: bool = True) -> dict[str, Any]:
    config, paths, baseline_config, baseline_paths = load_requirement_config(config_path)
    failures: list[str] = []
    try:
        assert_requirement_03_entry(config)
    except Exception as exc:
        failures.append(str(exc))
    required_paths = [paths.cache_dir / name for name in REQUIRED_CACHE]
    required_paths += [paths.reports_dir / name for name in REQUIRED_REPORTS]
    required_paths += [paths.manifests_dir / name for name in REQUIRED_MANIFESTS]
    for path in required_paths:
        if not path.exists():
            failures.append(f"missing required artifact: {relpath(path)}")
    if failures:
        raise RuntimeError("; ".join(failures))
    manifest_path = paths.manifests_dir / "requirement_04_holding_exit_manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("phase") != config["phase"]:
        failures.append("manifest phase mismatch")
    for key, rel in {
        "schedule_action_panel_hash": paths.cache_dir / "requirement_04_schedule_action_panel.parquet",
        "exposure_daily_panel_hash": paths.cache_dir / "requirement_04_exposure_daily_panel.parquet",
        "episode_schedule_summary_hash": paths.cache_dir / "requirement_04_episode_schedule_summary.parquet",
        "winner_state_event_panel_hash": paths.cache_dir / "requirement_04_winner_state_event_panel.parquet",
        "schedule_results_hash": paths.reports_dir / "requirement_04_schedule_results.csv",
        "schedule_comparison_hash": paths.reports_dir / "requirement_04_schedule_comparison.csv",
        "selected_schedule_hash": paths.reports_dir / "requirement_04_selected_schedule.csv",
        "big_winner_capture_audit_hash": paths.reports_dir / "requirement_04_big_winner_capture_audit.csv",
        "fast_fail_value_audit_hash": paths.reports_dir / "requirement_04_fast_fail_value_audit.csv",
        "winner_state_asof_audit_hash": paths.reports_dir / "requirement_04_winner_state_asof_audit.csv",
        "diagnostic_counterfactuals_hash": paths.reports_dir / "requirement_04_diagnostic_counterfactuals.csv",
        "gate_audit_hash": paths.reports_dir / "requirement_04_gate_audit.csv",
        "artifact_authority_hash": paths.reports_dir / "requirement_04_artifact_authority.csv",
    }.items():
        if manifest.get(key) != file_hash(rel):
            failures.append(f"manifest hash mismatch: {key}")
    actions = pd.read_parquet(paths.cache_dir / "requirement_04_schedule_action_panel.parquet")
    exposures = pd.read_parquet(paths.cache_dir / "requirement_04_exposure_daily_panel.parquet")
    summaries = pd.read_parquet(paths.cache_dir / "requirement_04_episode_schedule_summary.parquet")
    missing_action = set(base.action_columns()) - set(actions.columns)
    missing_exposure = set(base.exposure_columns()) - set(exposures.columns)
    if missing_action:
        failures.append(f"action schema missing columns: {sorted(missing_action)}")
    if missing_exposure:
        failures.append(f"exposure schema missing columns: {sorted(missing_exposure)}")
    for frame_name, frame in {"actions": actions, "exposures": exposures, "summaries": summaries}.items():
        if "variant_id" not in frame:
            failures.append(f"{frame_name} missing variant_id")
    selected = pd.read_csv(paths.reports_dir / "requirement_04_selected_schedule.csv")
    diagnostics = pd.read_csv(paths.reports_dir / "requirement_04_diagnostic_counterfactuals.csv")
    gates = pd.read_csv(paths.reports_dir / "requirement_04_gate_audit.csv")
    if BASELINE_SCHEDULE in set(selected["selected_schedule_id"].astype(str)):
        failures.append("baseline schedule was promoted")
    if diagnostics["eligible_for_selection"].astype(bool).any():
        failures.append("diagnostic row eligible_for_selection must be false")
    if not diagnostics.empty and diagnostics[["schedule_id", "variant_id", "split", "metric_name"]].duplicated().any():
        failures.append("diagnostic variant rows are not unique")
    asof = pd.read_csv(paths.reports_dir / "requirement_04_winner_state_asof_audit.csv")
    if not asof.empty:
        if asof.get("same_close_transition_used", pd.Series(False)).astype(bool).any():
            failures.append("winner-state same-close transition detected")
        if asof.get("effective_date_high_low_close_used_as_signal", pd.Series(False)).astype(bool).any():
            failures.append("winner-state effective-date data used as signal")
        if asof.get("future_target_label_used_as_signal", pd.Series(False)).astype(bool).any():
            failures.append("winner-state future target label used as signal")
    results = pd.read_csv(paths.reports_dir / "requirement_04_schedule_results.csv")
    if results["capital_occupancy_proxy"].isna().any():
        failures.append("capital_occupancy_proxy contains nulls")
    allowed_status = {"passed", "failed_contract_or_leakage", "failed_schedule_extension", "failed_winner_capture", "failed_tail_risk", "failed_robustness_holdout"}
    if manifest.get("next_phase_proceed_status") not in allowed_status:
        failures.append("invalid next_phase_proceed_status")
    hard_pass = bool(gates.loc[gates["is_hard_stop"].astype(bool), "passed"].astype(bool).all()) if not gates.empty else False
    if manifest.get("next_phase_proceed_status") == "passed" and not hard_pass:
        failures.append("manifest passed despite failed hard gates")
    if fail_on_gate_status and manifest.get("next_phase_proceed_status") != "passed":
        failures.append(f"Requirement 04 did not pass gates: {manifest.get('next_phase_proceed_status')}")
    if failures:
        raise RuntimeError("; ".join(failures))
    return {
        "validation_status": manifest.get("validation_status"),
        "next_phase_proceed_status": manifest.get("next_phase_proceed_status"),
        "recommendation": manifest.get("recommendation"),
        "selected_schedule_id": manifest.get("selected_requirement_04_schedule_id"),
        "gate_count": int(len(gates)),
        "passed_gate_count": int(gates["passed"].astype(bool).sum()) if "passed" in gates else 0,
        "failed_gate_count": int((~gates["passed"].astype(bool)).sum()) if "passed" in gates else 0,
    }
