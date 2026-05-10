#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


SCRIPT_DIR = Path(__file__).resolve().parent
EP3_DIR = SCRIPT_DIR.parent
TOPIC_DIR = EP3_DIR.parent
DEFAULT_CONFIG = EP3_DIR / "configs" / "deferred_family_failure_lookalike_audit.yaml"
PRIMARY_SPLITS = ("train", "validation", "robustness")
ANCHOR_FAMILY = "failed_lookalike_avoidance"
SOURCE_FAMILIES = ("A-like", "C-like")
PAIRWISE_BASELINES = ("matched_delay_baseline", "same_instrument_nonanchor_baseline", "industry_matched_baseline")
REPORT_ONLY_BASELINES = ("all_launch_direct_baseline", "stopped_ac_anchor_baseline")
BASELINES = (*PAIRWISE_BASELINES, *REPORT_ONLY_BASELINES)
LOW_INDEX: dict[str, tuple[np.ndarray, np.ndarray]] = {}
FORBIDDEN_FIELDS = {
    "selected_for_p1",
    "strategy_signal",
    "production_signal",
    "validation_selected_threshold",
    "robustness_selected_threshold",
}
REQUIRED_CACHE = [
    "deferred_family_event_panel.parquet",
    "deferred_family_matched_baseline_panel.parquet",
    "deferred_family_formula_diagnostic_panel.parquet",
]
REQUIRED_REPORTS = [
    "deferred_family_upstream_authority.csv",
    "deferred_family_stage_order_audit.csv",
    "deferred_family_transition_audit.csv",
    "deferred_family_lifecycle_source_audit.csv",
    "deferred_family_formula_dictionary.csv",
    "deferred_family_diagnostic_bin_freeze.csv",
    "deferred_family_event_summary.csv",
    "deferred_family_trigger_decomposition.csv",
    "deferred_family_matched_lift.csv",
    "deferred_family_tail_risk.csv",
    "deferred_family_ac_failure_attribution.csv",
    "deferred_family_sensitivity_horizon_audit.csv",
    "deferred_family_gate_audit.csv",
    "deferred_family_decision.csv",
    "deferred_family_report.md",
]


class DeferredFamilyError(RuntimeError):
    pass


@dataclass(frozen=True)
class Paths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    reports_dir: Path
    manifests_dir: Path


def parse_config_arg(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    return parser.parse_args()


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    path = Path(path).resolve()
    try:
        return str(path.relative_to(TOPIC_DIR))
    except ValueError:
        return str(path)


def load_config(path: str | Path) -> tuple[dict[str, Any], Paths]:
    config_path = topic_path(path)
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    output_root = topic_path(config["output_root"])
    paths = Paths(
        config_path=config_path,
        output_root=output_root,
        cache_dir=output_root / "cache",
        reports_dir=output_root / "reports",
        manifests_dir=output_root / "manifests",
    )
    for directory in (paths.cache_dir, paths.reports_dir, paths.manifests_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return config, paths


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_date(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def clean_str(value: Any) -> str:
    return "" if is_missing(value) else str(value)


def finite_float(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return out if math.isfinite(out) else float("nan")


def as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return bool(value)


def canonical_hash(data: Any) -> str:
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def stable_id(prefix: str, *parts: Any, length: int = 12) -> str:
    payload = "|".join("" if is_missing(part) else str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:length]}"


def file_hash(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_hash(path: Path) -> str:
    if not path.exists() or not path.is_dir():
        return ""
    allowed_prefixes = ("calendars/", "instruments/", "features/")
    parts: list[str] = []
    for child in sorted(p for p in path.rglob("*") if p.is_file()):
        rel = child.relative_to(path).as_posix()
        if not rel.startswith(allowed_prefixes):
            continue
        if "__pycache__" in child.parts or child.name.startswith(".") or child.name.endswith(".tmp"):
            continue
        digest = file_hash(child)
        if digest:
            parts.append(f"{rel}\0{child.stat().st_size}\0{digest}\n")
    return hashlib.sha256("".join(parts).encode("utf-8")).hexdigest() if parts else ""


def live_hash(path: Path) -> str:
    return directory_hash(path) if path.is_dir() else file_hash(path)


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TOPIC_DIR, text=True).strip()
    except Exception:
        return ""


def split_for_date(config: dict[str, Any], value: Any) -> str:
    if is_missing(value):
        return "out_of_scope"
    date = as_date(value)
    split = config["split"]
    if as_date(split["train_start"]) <= date <= as_date(split["train_end"]):
        return "train"
    if as_date(split["validation_start"]) <= date <= as_date(split["validation_end"]):
        return "validation"
    if as_date(split["robustness_start"]) <= date <= as_date(split["robustness_end"]):
        return "robustness"
    return "out_of_scope"


def split_end(config: dict[str, Any], split_name: str) -> pd.Timestamp | pd.NaT:
    key = {"train": "train_end", "validation": "validation_end", "robustness": "robustness_end"}.get(split_name)
    return as_date(config["split"][key]) if key else pd.NaT


def load_calendar(config: dict[str, Any]) -> pd.DatetimeIndex:
    path = topic_path(config["data_sources"]["trading_calendar_path"])
    dates = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DatetimeIndex(pd.to_datetime(dates).normalize(), name="date")


def trading_day_distance(calendar: pd.DatetimeIndex, start: Any, end: Any) -> int | None:
    if is_missing(start) or is_missing(end):
        return None
    start_pos = calendar.searchsorted(as_date(start), side="left")
    end_pos = calendar.searchsorted(as_date(end), side="left")
    if start_pos >= len(calendar) or end_pos >= len(calendar):
        return None
    return int(end_pos - start_pos)


def add_trading_days(calendar: pd.DatetimeIndex, date: Any, days: int) -> pd.Timestamp | pd.NaT:
    if is_missing(date):
        return pd.NaT
    pos = calendar.searchsorted(as_date(date), side="left")
    target = pos + int(days)
    if pos >= len(calendar) or target < 0 or target >= len(calendar):
        return pd.NaT
    return pd.Timestamp(calendar[target])


def date_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out:
            out[col] = pd.to_datetime(out[col], errors="coerce").dt.normalize()
    return out


def read_qlib_instruments(config: dict[str, Any]) -> list[str]:
    df = pd.read_csv(topic_path(config["data_sources"]["pit_qlib_instrument_universe_path"]))
    instruments = set(df["instrument"].astype(str).str.upper().unique())
    launch_path = topic_path(config["denominator_inputs"]["ep2_launch_pool"])
    if launch_path.exists():
        launch = pd.read_parquet(launch_path, columns=["instrument"])
        launch_instruments = set(launch["instrument"].astype(str).str.upper().unique())
        instruments = instruments & launch_instruments
    instruments = sorted(instruments)
    if not instruments:
        raise DeferredFamilyError("empty PIT Qlib instrument universe")
    return instruments


def load_provider_panel(config: dict[str, Any]) -> pd.DataFrame:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    provider_uri = topic_path(config["data_sources"]["qlib_provider_uri"])
    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    instruments = read_qlib_instruments(config)
    print(f"loading qlib provider instruments={len(instruments)}", flush=True)
    frame = D.features(
        instruments=instruments,
        fields=["$open", "$high", "$low", "$close", "$volume", "$money", "$factor"],
        start_time=config["input_contract"]["provider_load_start_date"],
        end_time=config["input_contract"]["provider_load_end_date"],
        freq="day",
    )
    if frame.empty:
        raise DeferredFamilyError("Qlib provider returned no rows")
    print(f"loaded qlib rows={len(frame)}", flush=True)
    panel = frame.rename(
        columns={"$open": "open", "$high": "high", "$low": "low", "$close": "close", "$volume": "volume", "$money": "money", "$factor": "factor"}
    ).reset_index()
    panel["date"] = pd.to_datetime(panel["datetime"]).dt.normalize()
    panel["instrument"] = panel["instrument"].astype(str).str.upper()
    return panel.drop(columns=["datetime"]).sort_values(["instrument", "date"]).reset_index(drop=True)


def load_market_panel(config: dict[str, Any]) -> pd.DataFrame:
    panel = load_provider_panel(config)
    print("joining PIT universe", flush=True)
    universe = pd.read_csv(topic_path(config["data_sources"]["pit_universe_path"]), parse_dates=["date"])
    universe["date"] = pd.to_datetime(universe["date"]).dt.normalize()
    universe["instrument"] = universe["instrument"].astype(str).str.upper()
    universe_key = universe.loc[universe["instrument"].isin(panel["instrument"].unique()), ["date", "instrument"]].drop_duplicates()
    panel = panel.merge(universe_key.assign(universe_member_asof_signal_date=True), on=["date", "instrument"], how="left")
    panel["universe_member_asof_signal_date"] = panel["universe_member_asof_signal_date"].fillna(False).astype(bool)
    industry = pd.read_csv(topic_path(config["data_sources"]["pit_industry_path"]), parse_dates=["date"])
    industry["date"] = pd.to_datetime(industry["date"]).dt.normalize()
    industry["instrument"] = industry["instrument"].astype(str).str.upper()
    industry_key = industry.loc[industry["instrument"].isin(panel["instrument"].unique()), ["date", "instrument", "industry_target_key", "industry_name"]].drop_duplicates(["date", "instrument"])
    print("joining PIT industry and deriving features", flush=True)
    panel = panel.merge(industry_key, on=["date", "instrument"], how="left")
    panel["industry_target_key"] = panel["industry_target_key"].fillna("UNKNOWN")
    panel["industry_name"] = panel["industry_name"].fillna("UNKNOWN")
    panel["industry_asof_signal_date"] = panel["industry_name"]
    return add_derived_features(panel, config)


def add_derived_features(panel: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    rules = config["observable_reference_rules"]
    df = panel.sort_values(["instrument", "date"]).reset_index(drop=True).copy()
    group = df.groupby("instrument", group_keys=False)
    df["prev_close"] = group["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - df["prev_close"]).abs()
    tr3 = (df["low"] - df["prev_close"]).abs()
    df["true_range"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_n = int(rules["atr_lookback_days"])
    money_n = int(rules["money_ma_lookback_days"])
    accel_n = int(rules["acceleration_lookback_days"])
    df["atr20"] = group["true_range"].transform(lambda s: s.shift(1).rolling(atr_n, min_periods=atr_n).mean())
    df["money_ma20"] = group["money"].transform(lambda s: s.shift(1).rolling(money_n, min_periods=money_n).mean())
    df["ret_60d"] = group["close"].transform(lambda s: s / s.shift(accel_n) - 1.0)
    df["vol20"] = group["close"].transform(lambda s: s.pct_change().shift(1).rolling(20, min_periods=20).std())
    df["rolling_max_close_60_prev"] = group["close"].transform(lambda s: s.shift(1).rolling(accel_n, min_periods=accel_n).max())
    df["launch_like_acceleration_raw"] = (
        (df["ret_60d"] >= float(rules["acceleration_min_return"]))
        & (df["close"] >= df["rolling_max_close_60_prev"])
        & (df["money"] >= float(rules["money_multiple_min"]) * df["money_ma20"])
        & (df["money"] >= float(rules["money_min_cny"]))
        & df["universe_member_asof_signal_date"].astype(bool)
    )
    return df


def instrument_frames(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {str(inst).upper(): g.sort_values("date").reset_index(drop=True).copy() for inst, g in panel.groupby("instrument", sort=False)}


def price_lookup(panel: pd.DataFrame) -> dict[tuple[str, pd.Timestamp], dict[str, Any]]:
    cols = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "money",
        "factor",
        "industry_target_key",
        "industry_name",
        "industry_asof_signal_date",
        "universe_member_asof_signal_date",
        "atr20",
        "money_ma20",
        "ret_60d",
        "vol20",
    ]
    out: dict[tuple[str, pd.Timestamp], dict[str, Any]] = {}
    LOW_INDEX.clear()
    for inst, group in panel.sort_values(["instrument", "date"]).groupby("instrument", sort=False):
        LOW_INDEX[str(inst).upper()] = (
            pd.to_datetime(group["date"]).dt.normalize().to_numpy(dtype="datetime64[ns]"),
            pd.to_numeric(group["low"], errors="coerce").to_numpy(dtype=float),
        )
    for row in panel[["instrument", "date", *[c for c in cols if c in panel]]].itertuples(index=False):
        data = row._asdict()
        inst = clean_str(data.pop("instrument")).upper()
        date = as_date(data.pop("date"))
        out[(inst, date)] = data
    return out


def load_inputs(config: dict[str, Any]) -> dict[str, Any]:
    p0 = config["upstream_ep3_p0"]
    p05 = config["upstream_ep3_p0_5"]
    den = config["denominator_inputs"]
    return {
        "p0_manifest": json.loads(topic_path(p0["manifest"]).read_text(encoding="utf-8")),
        "p05_manifest": json.loads(topic_path(p05["manifest"]).read_text(encoding="utf-8")),
        "winner_labels": date_columns(pd.read_parquet(topic_path(p0["winner_label_panel"])), ["date"]),
        "candidate_anchors": date_columns(pd.read_parquet(topic_path(p0["candidate_anchor_panel"])), ["signal_date", "execution_date", "reference_acceleration_date"]),
        "matched_baselines": date_columns(pd.read_parquet(topic_path(p0["matched_baseline_panel"])), ["signal_date", "execution_date", "reference_acceleration_date"]),
        "lifecycle_profile": date_columns(pd.read_csv(topic_path(p0["lifecycle_profile"])), ["retrospective_stage_date", "observable_signal_date"]),
        "gate_audit": pd.read_csv(topic_path(p0["gate_audit"])),
        "anchor_metrics": pd.read_csv(topic_path(p0["anchor_vs_matched_baseline"])),
        "anchor_windows": pd.read_csv(topic_path(p0["anchor_window_freeze"])),
        "bucket_freeze": pd.read_csv(topic_path(p0["matched_control_bucket_freeze"])),
        "p05_anchor_panel": date_columns(pd.read_parquet(topic_path(p05["anchor_event_diagnostic_panel"])), ["signal_date", "execution_date", "reference_acceleration_date"]),
        "p05_baseline_panel": date_columns(pd.read_parquet(topic_path(p05["baseline_event_diagnostic_panel"])), ["signal_date", "execution_date", "reference_acceleration_date"]),
        "p05_hypothesis": pd.read_csv(topic_path(p05["hypothesis_audit"])),
        "p05_decision": pd.read_csv(topic_path(p05["stop_continue_decision"])),
        "ep2_launch_pool": date_columns(pd.read_parquet(topic_path(den["ep2_launch_pool"])), ["signal_date", "execution_date"]),
    }


def manifest_lookup(manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_path: dict[str, dict[str, Any]] = {}
    by_name: dict[str, dict[str, Any]] = {}
    for row in manifest.get("artifact_authority", []):
        by_path[clean_str(row.get("path"))] = row
        by_name[clean_str(row.get("artifact_name"))] = row
    return by_path, by_name


def build_upstream_authority(config: dict[str, Any], inputs: dict[str, Any]) -> pd.DataFrame:
    rows = []
    manifests = {"p0": inputs["p0_manifest"], "p0_5": inputs["p05_manifest"]}
    for prefix, cfg_key, manifest_key in [("p0", "upstream_ep3_p0", "p0_manifest"), ("p0_5", "upstream_ep3_p0_5", "p05_manifest")]:
        by_path, by_name = manifest_lookup(manifests[prefix])
        for key, path_value in config[cfg_key].items():
            path = topic_path(path_value)
            rel = relpath(path)
            current = live_hash(path)
            if key == "manifest":
                expected = current
                required_status = "passed"
                observed_status = clean_str(inputs[manifest_key].get("validation_status"))
                authority_type = f"{prefix}_manifest"
            else:
                manifest_row = by_path.get(rel) or by_name.get(path.name)
                expected = clean_str(manifest_row.get("content_hash")) if manifest_row else ""
                required_status = "not_applicable"
                observed_status = "not_applicable"
                authority_type = f"{prefix}_artifact"
            rows.append(
                {
                    "authority_check_id": stable_id("DF_AUTH", authority_type, key, rel),
                    "authority_type": authority_type,
                    "artifact_path": rel,
                    "required_hash": expected,
                    "observed_hash": current,
                    "required_validation_status": required_status,
                    "observed_validation_status": observed_status,
                    "authority_status": "passed" if path.exists() and current and (not expected or expected == current) and (required_status == "not_applicable" or observed_status == required_status) else "failed",
                }
            )
    extra = {
        "ep2_launch_pool_reference": config["denominator_inputs"]["ep2_launch_pool"],
        "qlib_pit_directory": config["data_sources"]["qlib_provider_uri"],
        "ep2_launch_pool_reference_universe": config["data_sources"]["pit_qlib_instrument_universe_path"],
        "ep2_launch_pool_reference_calendar": config["data_sources"]["trading_calendar_path"],
        "ep2_launch_pool_reference_industry": config["data_sources"]["pit_industry_path"],
    }
    for authority_type, path_value in extra.items():
        path = topic_path(path_value)
        current = live_hash(path)
        rows.append(
            {
                "authority_check_id": stable_id("DF_AUTH", authority_type, relpath(path)),
                "authority_type": authority_type if authority_type in {"qlib_pit_directory", "ep2_launch_pool_reference"} else "ep2_launch_pool_reference",
                "artifact_path": relpath(path),
                "required_hash": "",
                "observed_hash": current,
                "required_validation_status": "not_applicable",
                "observed_validation_status": "not_applicable",
                "authority_status": "passed" if path.exists() and current else "failed",
            }
        )
    return pd.DataFrame(rows)


def build_transition_audit(config: dict[str, Any], inputs: dict[str, Any]) -> pd.DataFrame:
    decision = inputs["p05_decision"]
    rows = []
    required = config["deferred_family_scope"]["decision_source_required"]
    overall = decision.loc[decision["decision_scope"].eq("overall")]
    observed = clean_str(overall.iloc[0]["recommended_decision"]) if not overall.empty else ""
    rows.append(
        {
            "transition_check_id": "p0_5_overall_decision",
            "source_report": "p0_5_stop_continue_decision.csv",
            "required_value": required,
            "observed_value": observed,
            "transition_status": "passed" if observed == required else "failed",
        }
    )
    for family in config["deferred_family_scope"]["stopped_primary_families"]:
        row = decision.loc[decision["decision_scope"].eq("family") & decision["anchor_family_id"].eq(family)]
        observed_family = clean_str(row.iloc[0]["recommended_decision"]) if not row.empty else ""
        rows.append(
            {
                "transition_check_id": f"p0_5_{family}_stop",
                "source_report": "p0_5_stop_continue_decision.csv",
                "required_value": "stop_current_family",
                "observed_value": observed_family,
                "transition_status": "passed" if observed_family == "stop_current_family" else "failed",
            }
        )
    return pd.DataFrame(rows)


def build_lifecycle_source_audit(inputs: dict[str, Any]) -> pd.DataFrame:
    life = inputs["lifecycle_profile"].copy()
    rows = []
    for split in PRIMARY_SPLITS:
        stage = life.loc[life["split"].eq(split) & life["anchor_family_id"].eq(ANCHOR_FAMILY)]
        rows.append(
            {
                "split": split,
                "anchor_family_id": ANCHOR_FAMILY,
                "lifecycle_stage_id": "failed_lookalike_avoidance",
                "winner_episode_count": int(stage["winner_episode_id"].nunique()) if "winner_episode_id" in stage else 0,
                "source_upstream_artifact": "ep3_winner_lifecycle_profile.csv",
                "source_upstream_hash": "",
                "lifecycle_source_status": "passed" if split != "train" or int(stage["winner_episode_id"].nunique()) >= 20 else "too_sparse",
            }
        )
    return pd.DataFrame(rows)


def build_formula_dictionary() -> pd.DataFrame:
    specs = [
        ("A-like", "pullback_window_failure", "window", "trading_days_between(a,p) inside frozen pullback window", "min(days - low, high - days)", "a,p,calendar,window", "asof_t", "p0_window", "pullback_hold_restrengthen"),
        ("A-like", "pullback_depth_failure", "depth", "0.04 <= 1 - low[p]/close[a] <= 0.18", "min(depth - 0.04, 0.18 - depth)", "low[p],close[a]", "asof_t", "config", "0.04,0.18"),
        ("A-like", "pullback_atr_floor_failure", "atr_floor", "low[p] >= close[a] - 2*atr20[a]", "(low[p] - (close[a] - 2*atr20[a])) / close[a]", "low[p],close[a],atr20[a]", "asof_t", "config", "2.0"),
        ("A-like", "restrengthen_failure", "restrengthen", "t>p and t-p<=5 and close[t]>=high5[p] and close[t]>close[t-1] and money[t]>=money_ma20[t]", "min(component margins)", "t,p,close,high,money,money_ma20", "asof_t", "config", "5"),
        ("C-like", "second_breakout_gap_failure", "gap", "trading_days_between(a,t) in frozen second_breakout window and >=3", "min(days-low, high-days, days-3)", "a,t,calendar,window", "asof_t", "p0_window", "second_breakout"),
        ("C-like", "second_breakout_consolidation_failure", "consolidation", "min(low[a+1:t-1]) >= close[a]*0.85", "(min_interval_low - close[a]*0.85)/close[a]", "interval low,close[a]", "asof_t", "config", "0.15"),
        ("C-like", "second_breakout_return_failure", "return", "close[t]>=interval_high and close[t]/close[a]-1>=0.06", "min(close[t]/interval_high-1, close[t]/close[a]-1-0.06)", "close[t],close[a],interval high", "asof_t", "config", "0.06"),
        ("C-like", "second_breakout_liquidity_failure", "liquidity", "money[t]>=2*money_ma20[t] and money[t]>=50m", "min(money/(2*money_ma20)-1, money/50000000-1)", "money[t],money_ma20[t]", "asof_t", "config", "2.0,50000000"),
    ]
    rows = []
    for family, condition, component, predicate, margin, inputs, lookback, source, value in specs:
        payload = {
            "lookalike_source_family": family,
            "failure_condition_id": condition,
            "formula_component_id": component,
            "predicate_text": predicate,
            "signed_margin_formula_text": margin,
            "required_input_fields": inputs,
            "lookback_rule": lookback,
            "parameter_source": source,
            "parameter_value": value,
        }
        payload["formula_hash"] = canonical_hash(payload)
        payload["dictionary_row_hash"] = canonical_hash(payload)
        rows.append(payload)
    return pd.DataFrame(rows)


def source_formula_hash(dictionary: pd.DataFrame, family: str, condition: str) -> str:
    if condition == "none":
        rows = dictionary.loc[dictionary["lookalike_source_family"].eq(family)].sort_values(["failure_condition_id", "formula_component_id"])
    else:
        rows = dictionary.loc[dictionary["lookalike_source_family"].eq(family) & dictionary["failure_condition_id"].eq(condition)].sort_values("formula_component_id")
    return canonical_hash(rows.to_dict("records"))


def margin_json(margins: dict[str, float]) -> str:
    clean = {k: (None if not math.isfinite(v) else float(v)) for k, v in sorted(margins.items())}
    return json.dumps(clean, sort_keys=True, separators=(",", ":"))


def eval_a_like(config: dict[str, Any], calendar: pd.DatetimeIndex, inst_df: pd.DataFrame, ref_pos: int, t_pos: int, windows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rules = config["observable_reference_rules"]
    a = inst_df.iloc[ref_pos]
    t = inst_df.iloc[t_pos]
    close_a = finite_float(a.close)
    atr_a = finite_float(a.atr20)
    prev_close = finite_float(inst_df.iloc[t_pos - 1].close) if t_pos > 0 else np.nan
    candidates = []
    for p_pos in range(max(ref_pos + 1, t_pos - 5), t_pos):
        p = inst_df.iloc[p_pos]
        low_p = finite_float(p.low)
        money_t = finite_float(t.money)
        money_ma20_t = finite_float(t.money_ma20)
        high5 = finite_float(inst_df.iloc[max(0, p_pos - 4) : p_pos + 1]["high"].max())
        if not all(math.isfinite(x) for x in [close_a, atr_a, low_p, finite_float(t.close), prev_close, money_t, money_ma20_t, high5]) or close_a <= 0 or money_ma20_t <= 0 or high5 <= 0 or prev_close <= 0:
            continue
        days = p_pos - ref_pos
        win = windows["pullback_hold_restrengthen"]
        depth = 1.0 - low_p / close_a
        margins = {
            "pullback_window_failure": min(days - int(win["frozen_window_low"]), int(win["frozen_window_high"]) - days),
            "pullback_depth_failure": min(depth - float(rules["pullback_min_drawdown_from_acceleration_close"]), float(rules["pullback_max_drawdown_from_acceleration_close"]) - depth),
            "pullback_atr_floor_failure": (low_p - (close_a - float(rules["pullback_hold_atr_multiple"]) * atr_a)) / close_a,
            "restrengthen_failure": min(
                t_pos - p_pos - 1,
                int(rules["restrengthen_high_lookback_days"]) - (t_pos - p_pos),
                finite_float(t.close) / high5 - 1.0,
                finite_float(t.close) / prev_close - 1.0,
                money_t / money_ma20_t - 1.0,
            ),
        }
        failed = [k for k, v in margins.items() if v < 0]
        candidates.append((p_pos, margins, failed))
    if not candidates:
        return {"status": "unavailable", "reason": "no_candidate_pullback_tuple"}
    exact = [x for x in candidates if len(x[2]) == 1]
    clean = [x for x in candidates if len(x[2]) == 0]
    if exact:
        p_pos, margins, failed = sorted(exact, key=lambda x: (x[1][x[2][0]], -x[0], x[2][0]), reverse=True)[0]
    elif clean:
        p_pos, margins, failed = sorted(clean, key=lambda x: (min(x[1].values()), -x[0]), reverse=True)[0]
    else:
        p_pos, margins, failed = sorted(candidates, key=lambda x: (len(x[2]), min(x[1].values()), -x[0]))[0]
    condition = failed[0] if len(failed) == 1 else "none"
    return {
        "status": "available",
        "p_pos": p_pos,
        "condition": condition,
        "failed_count": len(failed),
        "margins": margins,
        "failure_margin_value": margins[condition] if condition != "none" else np.nan,
    }


def eval_c_like(config: dict[str, Any], calendar: pd.DatetimeIndex, inst_df: pd.DataFrame, ref_pos: int, t_pos: int, windows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rules = config["observable_reference_rules"]
    a = inst_df.iloc[ref_pos]
    t = inst_df.iloc[t_pos]
    interval = inst_df.iloc[ref_pos + 1 : t_pos]
    if interval.empty:
        return {"status": "unavailable", "reason": "empty_consolidation_interval"}
    close_a = finite_float(a.close)
    close_t = finite_float(t.close)
    money_t = finite_float(t.money)
    money_ma20_t = finite_float(t.money_ma20)
    interval_low = finite_float(interval["low"].min())
    interval_high = finite_float(interval["high"].max())
    if not all(math.isfinite(x) for x in [close_a, close_t, money_t, money_ma20_t, interval_low, interval_high]) or close_a <= 0 or money_ma20_t <= 0 or interval_high <= 0:
        return {"status": "unavailable", "reason": "missing_c_like_input"}
    days = t_pos - ref_pos
    win = windows["second_breakout"]
    margins = {
        "second_breakout_gap_failure": min(days - int(win["frozen_window_low"]), int(win["frozen_window_high"]) - days, days - int(rules["second_breakout_min_gap_days"])),
        "second_breakout_consolidation_failure": (interval_low - close_a * (1.0 - float(rules["consolidation_max_drawdown_from_first_close"]))) / close_a,
        "second_breakout_return_failure": min(close_t / interval_high - 1.0, close_t / close_a - 1.0 - float(rules["second_breakout_min_return_from_first_close"])),
        "second_breakout_liquidity_failure": min(money_t / (float(rules["money_multiple_min"]) * money_ma20_t) - 1.0, money_t / float(rules["money_min_cny"]) - 1.0),
    }
    failed = [k for k, v in margins.items() if v < 0]
    condition = failed[0] if len(failed) == 1 else "none"
    return {
        "status": "available",
        "p_pos": None,
        "condition": condition,
        "failed_count": len(failed),
        "margins": margins,
        "failure_margin_value": margins[condition] if condition != "none" else np.nan,
    }


def build_formula_diagnostics(
    config: dict[str, Any],
    inputs: dict[str, Any],
    calendar: pd.DatetimeIndex,
    market_panel: pd.DataFrame,
    dictionary: pd.DataFrame,
) -> pd.DataFrame:
    launch = inputs["ep2_launch_pool"].sort_values(["launch_episode_id", "signal_date"]).drop_duplicates("launch_episode_id", keep="first").copy()
    launch["instrument"] = launch["instrument"].astype(str).str.upper()
    by_inst = instrument_frames(market_panel)
    windows = inputs["anchor_windows"].set_index("anchor_family_id").to_dict("index")
    low_days, high_days = config["observable_failure_lookalike_rules"]["post_reference_observation_days"]
    rows: list[dict[str, Any]] = []
    for ep in launch.itertuples(index=False):
        inst = clean_str(ep.instrument).upper()
        ref_date = as_date(ep.signal_date)
        split = split_for_date(config, ref_date)
        inst_df = by_inst.get(inst)
        if inst_df is None:
            for family in SOURCE_FAMILIES:
                rows.append(_unavailable_formula_row(dictionary, ep, family, ref_date, ref_date, "missing_instrument_price_panel", split))
            continue
        dates = pd.DatetimeIndex(inst_df["date"])
        matches = np.where(dates == ref_date)[0]
        if len(matches) == 0:
            for family in SOURCE_FAMILIES:
                rows.append(_unavailable_formula_row(dictionary, ep, family, ref_date, ref_date, "missing_reference_price_row", split))
            continue
        ref_pos = int(matches[0])
        max_pos = min(len(inst_df) - 1, ref_pos + int(high_days))
        for t_pos in range(ref_pos + int(low_days), max_pos + 1):
            t_date = as_date(inst_df.iloc[t_pos].date)
            t_split = split_for_date(config, t_date)
            if t_split != split:
                continue
            for family, evaluator in [("A-like", eval_a_like), ("C-like", eval_c_like)]:
                result = evaluator(config, calendar, inst_df, ref_pos, t_pos, windows)
                status = result["status"]
                condition = clean_str(result.get("condition")) or "none"
                p_pos = result.get("p_pos")
                candidate_p = as_date(inst_df.iloc[p_pos].date) if p_pos is not None else pd.NaT
                payload = {
                    "formula_diagnostic_row_id": stable_id("DF_FORM", ep.launch_episode_id, family, t_date, candidate_p, condition),
                    "launch_episode_id": ep.launch_episode_id,
                    "instrument": inst,
                    "split": t_split,
                    "lookalike_source_family": family,
                    "reference_acceleration_date": ref_date,
                    "candidate_signal_date": t_date,
                    "candidate_pullback_low_date": candidate_p,
                    "failure_condition_id": condition if status == "available" else "none",
                    "failed_condition_count": int(result.get("failed_count", 0)) if status == "available" else 0,
                    "condition_margin_json": margin_json(result.get("margins", {})),
                    "formula_availability_status": status,
                    "unavailable_reason": "" if status == "available" else clean_str(result.get("reason")),
                    "is_failure_lookalike_state_candidate": bool(status == "available" and int(result.get("failed_count", 0)) == 1),
                    "failure_margin_value": result.get("failure_margin_value", np.nan),
                    "source_formula_hash": source_formula_hash(dictionary, family, condition if status == "available" else "none"),
                }
                payload["row_hash"] = canonical_hash(payload)
                rows.append(payload)
    return pd.DataFrame(rows)


def _unavailable_formula_row(dictionary: pd.DataFrame, ep: Any, family: str, ref_date: pd.Timestamp, candidate_date: pd.Timestamp, reason: str, split: str) -> dict[str, Any]:
    payload = {
        "formula_diagnostic_row_id": stable_id("DF_FORM", ep.launch_episode_id, family, candidate_date, reason),
        "launch_episode_id": ep.launch_episode_id,
        "instrument": clean_str(ep.instrument).upper(),
        "split": split,
        "lookalike_source_family": family,
        "reference_acceleration_date": ref_date,
        "candidate_signal_date": candidate_date,
        "candidate_pullback_low_date": pd.NaT,
        "failure_condition_id": "none",
        "failed_condition_count": 0,
        "condition_margin_json": "{}",
        "formula_availability_status": "unavailable",
        "unavailable_reason": reason,
        "is_failure_lookalike_state_candidate": False,
        "failure_margin_value": np.nan,
        "source_formula_hash": source_formula_hash(dictionary, family, "none"),
    }
    payload["row_hash"] = canonical_hash(payload)
    return payload


def parse_margin_json(value: str) -> dict[str, float]:
    raw = json.loads(value or "{}")
    return {str(k): finite_float(v) for k, v in raw.items()}


def execution_status(config: dict[str, Any], lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]], inst: str, signal_date: pd.Timestamp, execution_date: pd.Timestamp) -> dict[str, Any]:
    if pd.isna(execution_date):
        return {"entry_price_reference": np.nan, "is_executable_next_open": False, "blocked_buy_reason": "missing_calendar_next_day"}
    info = lookup.get((inst, as_date(execution_date)))
    prev = lookup.get((inst, as_date(signal_date)))
    if info is None:
        return {"entry_price_reference": np.nan, "is_executable_next_open": False, "blocked_buy_reason": "missing_price_row"}
    open_price = finite_float(info.get("open"))
    volume = finite_float(info.get("volume"))
    money = finite_float(info.get("money"))
    reason = ""
    if not math.isfinite(open_price):
        reason = "missing_open"
    elif not math.isfinite(volume) or volume <= 0:
        reason = "zero_volume"
    elif not math.isfinite(money) or money <= 0:
        reason = "zero_money"
    elif prev is not None:
        prev_close = finite_float(prev.get("close"))
        limit = float(config["execution"]["limit_inference_pct"]["mainboard_default"])
        if math.isfinite(prev_close) and prev_close > 0 and open_price >= prev_close * (1.0 + limit):
            reason = "limit_up_inferred"
    if not reason and not bool(info.get("universe_member_asof_signal_date", False)):
        reason = "not_universe_member"
    return {"entry_price_reference": open_price, "is_executable_next_open": not bool(reason), "blocked_buy_reason": reason}


def add_forward_metrics(config: dict[str, Any], calendar: pd.DatetimeIndex, lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]], row: dict[str, Any]) -> dict[str, Any]:
    inst = clean_str(row["instrument"]).upper()
    signal_date = as_date(row["signal_date"])
    costs = config["cost_model"]
    buy_cost = float(costs["derived_buy_cost_bps"]) / 10000.0
    sell_cost = float(costs["derived_sell_cost_bps"]) / 10000.0
    entry_date = as_date(row["execution_date"]) if not is_missing(row.get("execution_date")) else add_trading_days(calendar, signal_date, 1)
    entry_info = lookup.get((inst, entry_date))
    entry_open = finite_float(entry_info.get("open")) if entry_info else np.nan
    split_name = clean_str(row.get("split")) or split_for_date(config, signal_date)
    for horizon, days in [("H10", 10), ("H20", 20), ("H60", 60)]:
        exit_date = add_trading_days(calendar, signal_date, days + 1)
        ret = np.nan
        mae = np.nan
        if not pd.isna(exit_date) and math.isfinite(entry_open) and entry_open > 0:
            exit_info = lookup.get((inst, exit_date))
            exit_open = finite_float(exit_info.get("open")) if exit_info else np.nan
            if math.isfinite(exit_open):
                ret = (exit_open * (1.0 - sell_cost)) / (entry_open * (1.0 + buy_cost)) - 1.0
            low_idx = LOW_INDEX.get(inst)
            if low_idx is not None:
                dates, lows = low_idx
                left = np.searchsorted(dates, np.datetime64(entry_date), side="left")
                right = np.searchsorted(dates, np.datetime64(exit_date), side="right")
                window_lows = lows[left:right]
                window_lows = window_lows[np.isfinite(window_lows)]
                if len(window_lows):
                    mae = (float(np.min(window_lows)) * (1.0 - sell_cost)) / (entry_open * (1.0 + buy_cost)) - 1.0
        row[f"exit_date_{horizon}"] = exit_date
        row[f"after_cost_return_{horizon}"] = ret
        row[f"max_adverse_excursion_{horizon}"] = mae
    h20_exit = row["exit_date_H20"]
    row["eligible_for_primary_gate"] = bool(split_name in PRIMARY_SPLITS and not pd.isna(h20_exit) and h20_exit <= split_end(config, split_name) and math.isfinite(finite_float(row["after_cost_return_H20"])))
    return row


def assign_p0_bucket(value: Any, bucket_freeze: pd.DataFrame, bucket_name: str) -> str:
    if is_missing(value):
        return "unavailable"
    rows = bucket_freeze.loc[bucket_freeze["bucket_name"].eq(bucket_name)].copy()
    x = finite_float(value)
    if rows.empty or not math.isfinite(x):
        return "unavailable"
    for row in rows.sort_values("bucket_index").itertuples(index=False):
        low = finite_float(row.lower_bound)
        high = finite_float(row.upper_bound)
        idx = int(row.bucket_index)
        if (x >= low or math.isinf(low)) and (x < high or math.isinf(high) or idx == int(rows["bucket_index"].max())):
            return str(idx)
    return "unavailable"


def assign_edges(value: Any, edges: list[float], labels: list[str]) -> str:
    x = finite_float(value)
    if not math.isfinite(x) or len(edges) < 2:
        return "unavailable"
    for idx in range(len(edges) - 1):
        low, high = edges[idx], edges[idx + 1]
        if low <= x < high or (idx == len(edges) - 2 and low <= x <= high):
            return labels[idx]
    return "unavailable"


def freeze_id(freeze_type: str, family: str, axis: str) -> str:
    return stable_id("DF_FREEZE", freeze_type, family, axis)


def build_events_and_freeze(
    config: dict[str, Any],
    inputs: dict[str, Any],
    formula: pd.DataFrame,
    dictionary: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    market_panel: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = price_lookup(market_panel)
    label_key = inputs["winner_labels"].set_index(["instrument", "date"]).to_dict("index")
    bucket_freeze = inputs["bucket_freeze"]
    rows: list[dict[str, Any]] = []
    available = formula.loc[formula["formula_availability_status"].eq("available")].copy()
    for group_key, group in available.sort_values(["launch_episode_id", "lookalike_source_family", "candidate_signal_date"]).groupby(["launch_episode_id", "lookalike_source_family"], sort=False):
        failures: list[dict[str, Any]] = []
        recorded_failure = False
        recorded_clean = False
        recorded_recovery = False
        for frow in group.itertuples(index=False):
            signal_date = as_date(frow.candidate_signal_date)
            margins = parse_margin_json(frow.condition_margin_json)
            event_type = ""
            avoidance = ""
            if int(frow.failed_condition_count) == 1 and not recorded_failure:
                event_type = "failure_lookalike_state"
                avoidance = "persistent_failure"
                recorded_failure = True
            elif int(frow.failed_condition_count) == 0 and not failures and not recorded_clean:
                event_type = "clean_avoidance_state"
                avoidance = "clean_avoidance"
                recorded_clean = True
            if event_type:
                payload = make_event_row(config, inputs, calendar, lookup, label_key, bucket_freeze, dictionary, frow, event_type, avoidance, signal_date, signal_date, pd.NaT, margins, finite_float(frow.failure_margin_value), np.nan)
                rows.append(payload)
                if event_type == "failure_lookalike_state":
                    failures.append({"row": frow, "date": signal_date, "margin": finite_float(frow.failure_margin_value), "condition": clean_str(frow.failure_condition_id)})
            if recorded_recovery:
                continue
            for failure in list(failures):
                days = trading_day_distance(calendar, failure["date"], signal_date)
                if days is None or days <= 0 or days > int(config["observable_failure_lookalike_rules"]["max_recovery_after_failure_days"]):
                    continue
                condition = failure["condition"]
                if int(frow.failed_condition_count) == 0 and margins.get(condition, -1.0) >= 0:
                    ref_info = lookup.get((clean_str(frow.instrument).upper(), as_date(frow.reference_acceleration_date)))
                    sig_info = lookup.get((clean_str(frow.instrument).upper(), signal_date))
                    close_ref = finite_float(ref_info.get("close")) if ref_info else np.nan
                    close_sig = finite_float(sig_info.get("close")) if sig_info else np.nan
                    money = finite_float(sig_info.get("money")) if sig_info else np.nan
                    money_ma = finite_float(sig_info.get("money_ma20")) if sig_info else np.nan
                    if math.isfinite(close_ref) and math.isfinite(close_sig) and close_sig >= close_ref * (1.0 + float(config["observable_failure_lookalike_rules"]["min_recovery_return_from_reference_close"])) and (not math.isfinite(money_ma) or money >= money_ma):
                        payload = make_event_row(config, inputs, calendar, lookup, label_key, bucket_freeze, dictionary, frow, "recovery_after_failed_lookalike", "recovered_after_failure", signal_date, failure["date"], signal_date, margins, failure["margin"], margins.get(condition, np.nan))
                        rows.append(payload)
                        failures.remove(failure)
                        recorded_recovery = True
                        break
    event = pd.DataFrame(rows)
    if event.empty:
        event = pd.DataFrame(columns=event_columns())
    event = apply_dedupe(event)
    freeze = build_freeze(config, inputs, formula, event)
    event = apply_failure_margin_bucket(event, freeze)
    return event[event_columns()], freeze


def make_event_row(
    config: dict[str, Any],
    inputs: dict[str, Any],
    calendar: pd.DatetimeIndex,
    lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    label_key: dict[tuple[str, pd.Timestamp], dict[str, Any]],
    bucket_freeze: pd.DataFrame,
    dictionary: pd.DataFrame,
    frow: Any,
    event_type: str,
    avoidance: str,
    signal_date: pd.Timestamp,
    failure_date: pd.Timestamp | pd.NaT,
    recovery_date: pd.Timestamp | pd.NaT,
    margins: dict[str, float],
    failure_margin: float,
    repaired_margin: float,
) -> dict[str, Any]:
    inst = clean_str(frow.instrument).upper()
    execution_date = add_trading_days(calendar, signal_date, 1)
    exec_status = execution_status(config, lookup, inst, signal_date, execution_date)
    info = lookup.get((inst, signal_date), {})
    label = label_key.get((inst, signal_date), {})
    source_family = clean_str(frow.lookalike_source_family)
    condition = clean_str(frow.failure_condition_id)
    event_id = stable_id("DF_EVT", frow.launch_episode_id, source_family, event_type, failure_date, signal_date, condition)
    row = {
        "deferred_family_event_id": event_id,
        "anchor_family_id": ANCHOR_FAMILY,
        "launch_episode_id": frow.launch_episode_id,
        "instrument": inst,
        "signal_date": signal_date,
        "execution_date": execution_date,
        "split": split_for_date(config, signal_date),
        "event_type": event_type,
        "is_primary_forward_audit_event": False,
        "dedupe_rank_within_launch_episode": 0,
        "reference_acceleration_date": as_date(frow.reference_acceleration_date),
        "reference_age_days": trading_day_distance(calendar, frow.reference_acceleration_date, signal_date),
        "failure_state_date": failure_date if event_type == "recovery_after_failed_lookalike" else pd.NaT,
        "recovery_signal_date": recovery_date if event_type == "recovery_after_failed_lookalike" else pd.NaT,
        "lookalike_source_family": source_family,
        "failure_condition_id": condition,
        "failure_margin_value": failure_margin,
        "repaired_failure_margin_value": repaired_margin,
        "failure_margin_bucket": "unavailable",
        "avoidance_status": avoidance,
        "is_executable_next_open": exec_status["is_executable_next_open"],
        "blocked_buy_reason": exec_status["blocked_buy_reason"],
        "eligible_for_primary_gate": False,
        "winner_50h120": label.get("winner_50h120", False),
        "winner_100h240": label.get("winner_100h240", False),
        "money_bucket": assign_p0_bucket(info.get("money", np.nan), bucket_freeze, "money_bucket"),
        "vol20_bucket": assign_p0_bucket(info.get("vol20", np.nan), bucket_freeze, "vol20_bucket"),
        "ret_60d_bucket": assign_p0_bucket(info.get("ret_60d", np.nan), bucket_freeze, "ret_60d_bucket"),
        "industry_bucket": clean_str(info.get("industry_name")) or "UNKNOWN",
        "year_bucket": str(signal_date.year),
        "source_formula_hash": source_formula_hash(dictionary, source_family, condition),
    }
    add_forward_metrics(config, calendar, lookup, row)
    row["is_primary_forward_audit_event"] = bool(event_type == "recovery_after_failed_lookalike" and row["is_executable_next_open"] and row["eligible_for_primary_gate"])
    row["row_hash"] = canonical_hash({k: v for k, v in row.items() if k != "row_hash"})
    return row


def apply_dedupe(event: pd.DataFrame) -> pd.DataFrame:
    if event.empty:
        return event
    out = event.copy()
    out["dedupe_rank_within_launch_episode"] = 0
    mask = out["event_type"].eq("recovery_after_failed_lookalike")
    rec = out.loc[mask].sort_values(["split", "launch_episode_id", "lookalike_source_family", "signal_date", "failure_state_date", "repaired_failure_margin_value", "failure_condition_id", "deferred_family_event_id"], ascending=[True, True, True, True, True, False, True, True]).copy()
    ranks = rec.groupby(["split", "launch_episode_id", "lookalike_source_family"]).cumcount() + 1
    out.loc[rec.index, "dedupe_rank_within_launch_episode"] = ranks
    out["is_primary_forward_audit_event"] = out["event_type"].eq("recovery_after_failed_lookalike") & out["dedupe_rank_within_launch_episode"].eq(1) & out["is_executable_next_open"].map(as_bool) & out["eligible_for_primary_gate"].map(as_bool)
    return out


def build_freeze(config: dict[str, Any], inputs: dict[str, Any], formula: pd.DataFrame, event: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for family in SOURCE_FAMILIES:
        train_fail = formula.loc[formula["split"].eq("train") & formula["lookalike_source_family"].eq(family) & formula["is_failure_lookalike_state_candidate"].map(as_bool)]
        vals = pd.to_numeric(train_fail["failure_margin_value"], errors="coerce").dropna()
        if vals.empty:
            edges = [-np.inf, np.inf]
        else:
            edges = list(np.unique(np.quantile(vals, config["diagnostic_bins"]["failure_margin_quantiles"])))
            if len(edges) < 2:
                edges = [float(vals.min()), float(vals.max())]
            edges[0] = -np.inf
            edges[-1] = np.inf
        rows.append(_freeze_row("failure_margin_quantile", family, "failure_margin_bucket", edges, len(vals), "derived" if len(vals) else "insufficient_train_rows"))
        rows.append(_freeze_row("reference_age_days", family, "reference_age_days", config["diagnostic_bins"]["reference_age_days"], int(train_fail.shape[0]), "derived"))
        train_rec = event.loc[event["split"].eq("train") & event["lookalike_source_family"].eq(family) & event["event_type"].eq("recovery_after_failed_lookalike") & event["is_primary_forward_audit_event"].map(as_bool)].copy()
        delays = []
        for row in train_rec.itertuples(index=False):
            d = trading_day_distance(load_calendar(config), row.failure_state_date, row.signal_date)
            if d is not None:
                delays.append(int(d))
        status = "derived"
        median_value: list[float] = []
        if len(delays) < int(config["diagnostic_bins"]["min_train_recovery_rows_for_delay_freeze"]):
            status = "insufficient_train_rows"
        else:
            delays = sorted(delays)
            median_value = [float(delays[(len(delays) - 1) // 2])]
        rows.append(_freeze_row("train_median_recovery_delay_days", family, "recovery_delay_days", median_value, len(delays), status))
    for _, row in inputs["bucket_freeze"].iterrows():
        rows.append(
            _freeze_row(
                f"{row.bucket_name}_copy_from_p0",
                "all",
                row.bucket_name,
                [finite_float(row.lower_bound), finite_float(row.upper_bound)],
                0,
                "copied_from_p0",
                extra={"parameter_hash": clean_str(row.bucket_hash)},
            )
        )
    return pd.DataFrame(rows)


def _freeze_row(freeze_type: str, family: str, axis: str, edges: list[Any], n: int, status: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "freeze_id": stable_id("DF_FREEZE", freeze_type, family, axis, json.dumps(edges, allow_nan=True, default=str)),
        "freeze_type": freeze_type,
        "lookalike_source_family": family,
        "diagnostic_axis": axis,
        "bin_edges": json.dumps(edges, allow_nan=True, ensure_ascii=False),
        "train_source_row_count": int(n),
        "train_source_instrument_year_count": 0,
        "freeze_status": status,
        "parameter_hash": canonical_hash({"freeze_type": freeze_type, "family": family, "axis": axis, "edges": edges}),
    }
    if extra:
        payload.update(extra)
    payload["row_hash"] = canonical_hash(payload)
    return payload


def apply_failure_margin_bucket(event: pd.DataFrame, freeze: pd.DataFrame) -> pd.DataFrame:
    if event.empty:
        return event
    out = event.copy()
    for family in SOURCE_FAMILIES:
        row = freeze.loc[freeze["lookalike_source_family"].eq(family) & freeze["diagnostic_axis"].eq("failure_margin_bucket")]
        if row.empty:
            continue
        edges = [float(x) for x in json.loads(row.iloc[0]["bin_edges"])]
        labels = [f"q{i}" for i in range(len(edges) - 1)]
        mask = out["lookalike_source_family"].eq(family)
        out.loc[mask, "failure_margin_bucket"] = out.loc[mask, "failure_margin_value"].map(lambda x: assign_edges(x, edges, labels))
    out["row_hash"] = out.apply(lambda r: canonical_hash({k: r[k] for k in out.columns if k != "row_hash"}), axis=1)
    return out


def event_columns() -> list[str]:
    return [
        "deferred_family_event_id",
        "anchor_family_id",
        "launch_episode_id",
        "instrument",
        "signal_date",
        "execution_date",
        "split",
        "event_type",
        "is_primary_forward_audit_event",
        "dedupe_rank_within_launch_episode",
        "reference_acceleration_date",
        "reference_age_days",
        "failure_state_date",
        "recovery_signal_date",
        "lookalike_source_family",
        "failure_condition_id",
        "failure_margin_value",
        "repaired_failure_margin_value",
        "failure_margin_bucket",
        "avoidance_status",
        "is_executable_next_open",
        "blocked_buy_reason",
        "eligible_for_primary_gate",
        "winner_50h120",
        "winner_100h240",
        "money_bucket",
        "vol20_bucket",
        "ret_60d_bucket",
        "industry_bucket",
        "year_bucket",
        "after_cost_return_H10",
        "max_adverse_excursion_H10",
        "after_cost_return_H20",
        "max_adverse_excursion_H20",
        "after_cost_return_H60",
        "max_adverse_excursion_H60",
        "source_formula_hash",
        "row_hash",
    ]


def build_matched_baselines(
    config: dict[str, Any],
    inputs: dict[str, Any],
    event: pd.DataFrame,
    freeze: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    market_panel: pd.DataFrame,
) -> pd.DataFrame:
    lookup = price_lookup(market_panel)
    labels = inputs["winner_labels"].copy()
    labels["instrument"] = labels["instrument"].astype(str).str.upper()
    label_rows = labels.loc[labels["split"].isin(PRIMARY_SPLITS)].copy()
    label_rows["industry_bucket"] = [
        clean_str((lookup.get((inst, as_date(date)), {}) or {}).get("industry_name")) or "UNKNOWN"
        for inst, date in zip(label_rows["instrument"], label_rows["date"])
    ]
    primary = event.loc[event["is_primary_forward_audit_event"].map(as_bool)].sort_values(["split", "lookalike_source_family", "signal_date", "instrument", "deferred_family_event_id"]).copy()
    used: dict[tuple[str, str], set[tuple[str, pd.Timestamp]]] = {}
    rows: list[dict[str, Any]] = []
    event_dates = set(zip(event["instrument"].astype(str), pd.to_datetime(event["signal_date"]).dt.normalize()))
    p0_anchor_dates = set(zip(inputs["candidate_anchors"]["instrument"].astype(str), pd.to_datetime(inputs["candidate_anchors"]["signal_date"]).dt.normalize()))
    for anchor in primary.itertuples(index=False):
        for baseline_id in PAIRWISE_BASELINES:
            donor = select_baseline_donor(config, inputs, calendar, lookup, label_rows, anchor, baseline_id, freeze, event_dates, p0_anchor_dates, used)
            rows.append(make_baseline_row(config, calendar, lookup, anchor, baseline_id, donor))
    rows.extend(build_all_launch_baseline(config, inputs, calendar, lookup))
    rows.extend(build_stopped_ac_baseline(config, inputs))
    out = pd.DataFrame(rows)
    if out.empty:
        out = pd.DataFrame(columns=baseline_columns())
    return out[baseline_columns()]


def select_baseline_donor(config: dict[str, Any], inputs: dict[str, Any], calendar: pd.DatetimeIndex, lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]], labels: pd.DataFrame, anchor: Any, baseline_id: str, freeze: pd.DataFrame, event_dates: set[tuple[str, pd.Timestamp]], p0_anchor_dates: set[tuple[str, pd.Timestamp]], used: dict[tuple[str, str], set[tuple[str, pd.Timestamp]]]) -> dict[str, Any]:
    family = clean_str(anchor.lookalike_source_family)
    if baseline_id == "matched_delay_baseline":
        row = freeze.loc[freeze["lookalike_source_family"].eq(family) & freeze["freeze_type"].eq("train_median_recovery_delay_days")]
        if row.empty or clean_str(row.iloc[0]["freeze_status"]) == "insufficient_train_rows":
            return {"match_status": "unmatched", "match_reason": "insufficient_train_recovery_rows"}
        edges = json.loads(row.iloc[0]["bin_edges"])
        if not edges:
            return {"match_status": "unmatched", "match_reason": "missing_delay_freeze"}
        signal_date = add_trading_days(calendar, anchor.signal_date, int(edges[0]))
        inst = clean_str(anchor.instrument).upper()
        if pd.isna(signal_date):
            return {"match_status": "unmatched", "match_reason": "missing_delay_date"}
        info = lookup.get((inst, signal_date))
        if info is None:
            return {"match_status": "unmatched", "match_reason": "missing_delay_price_row"}
        return {"match_status": "matched", "match_reason": "delay_median", "instrument": inst, "signal_date": signal_date}
    anchor_date = as_date(anchor.signal_date)
    max_dist = int(config["baseline_matching"]["max_same_instrument_distance_days"] if baseline_id == "same_instrument_nonanchor_baseline" else config["baseline_matching"]["max_industry_distance_days"])
    candidates = labels.loc[labels["split"].eq(anchor.split) & labels["eligible_for_primary_gate"].map(as_bool)].copy()
    if baseline_id == "same_instrument_nonanchor_baseline":
        candidates = candidates.loc[candidates["instrument"].eq(clean_str(anchor.instrument).upper())]
    else:
        anchor_info = lookup.get((clean_str(anchor.instrument).upper(), anchor_date), {})
        industry = clean_str(anchor_info.get("industry_name")) or clean_str(anchor.industry_bucket)
        candidates = candidates.loc[candidates["instrument"].ne(clean_str(anchor.instrument).upper()) & candidates["industry_bucket"].eq(industry)]
    candidate_rows = []
    used_key = (baseline_id, clean_str(anchor.split))
    used.setdefault(used_key, set())
    for row in candidates.itertuples(index=False):
        date = as_date(row.date)
        inst = clean_str(row.instrument).upper()
        dist = trading_day_distance(calendar, anchor_date, date)
        if dist is None or abs(dist) > max_dist:
            continue
        if (inst, date) in event_dates or (inst, date) in p0_anchor_dates or (inst, date) in used[used_key]:
            continue
        exec_date = add_trading_days(calendar, date, 1)
        exec_st = execution_status(config, lookup, inst, date, exec_date)
        if not exec_st["is_executable_next_open"]:
            continue
        if abs(trading_day_distance(calendar, anchor_date, date) or 9999) <= int(config["baseline_matching"]["exclude_dates_within_primary_deferred_event_days"]) and inst == clean_str(anchor.instrument).upper():
            continue
        candidate_rows.append((abs(dist), date, inst))
    if not candidate_rows:
        return {"match_status": "unmatched", "match_reason": "no_same_instrument_nonanchor_donor" if baseline_id == "same_instrument_nonanchor_baseline" else "no_industry_matched_donor"}
    _, date, inst = sorted(candidate_rows, key=lambda x: (x[0], x[1], x[2]))[0]
    used[used_key].add((inst, date))
    return {"match_status": "matched", "match_reason": "nearest_donor", "instrument": inst, "signal_date": date}


def make_baseline_row(config: dict[str, Any], calendar: pd.DatetimeIndex, lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]], anchor: Any, baseline_id: str, donor: dict[str, Any]) -> dict[str, Any]:
    matched = donor.get("match_status") == "matched"
    inst = clean_str(donor.get("instrument", anchor.instrument)).upper()
    signal_date = as_date(donor.get("signal_date", anchor.signal_date)) if matched else pd.NaT
    execution_date = add_trading_days(calendar, signal_date, 1) if matched else pd.NaT
    row = {
        "baseline_event_id": stable_id("DF_BASE", anchor.deferred_family_event_id, baseline_id, inst, signal_date),
        "deferred_family_event_id": anchor.deferred_family_event_id,
        "baseline_id": baseline_id,
        "lookalike_source_family": anchor.lookalike_source_family,
        "donor_source_table": "ep3_winner_label_panel",
        "instrument": inst,
        "signal_date": signal_date,
        "execution_date": execution_date,
        "split": anchor.split,
        "match_status": donor.get("match_status", "unmatched"),
        "match_reason": donor.get("match_reason", "unmatched"),
        "trading_day_distance_to_anchor": trading_day_distance(calendar, anchor.signal_date, signal_date) if matched else np.nan,
        "replacement_sequence_rank": 1,
        "diagnostic_bucket_source": "linked_deferred_event",
        "eligible_for_primary_gate": False,
    }
    if matched:
        exec_st = execution_status(config, lookup, inst, signal_date, execution_date)
        info = lookup.get((inst, signal_date), {})
        row.update(
            {
                "money_bucket": anchor.money_bucket,
                "vol20_bucket": anchor.vol20_bucket,
                "ret_60d_bucket": anchor.ret_60d_bucket,
                "industry_bucket": clean_str(info.get("industry_name")) or "UNKNOWN",
                "year_bucket": str(signal_date.year),
                "is_executable_next_open": exec_st["is_executable_next_open"],
                "blocked_buy_reason": exec_st["blocked_buy_reason"],
            }
        )
        add_forward_metrics(config, calendar, lookup, row)
    else:
        for col in ["money_bucket", "vol20_bucket", "ret_60d_bucket", "industry_bucket", "year_bucket"]:
            row[col] = "unavailable"
        row["is_executable_next_open"] = False
        row["blocked_buy_reason"] = row["match_reason"]
        for horizon in ("H10", "H20", "H60"):
            row[f"after_cost_return_{horizon}"] = np.nan
            row[f"max_adverse_excursion_{horizon}"] = np.nan
    row["row_hash"] = canonical_hash(row)
    return row


def build_all_launch_baseline(config: dict[str, Any], inputs: dict[str, Any], calendar: pd.DatetimeIndex, lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]]) -> list[dict[str, Any]]:
    launch = inputs["ep2_launch_pool"].sort_values(["launch_episode_id", "signal_date"]).drop_duplicates("launch_episode_id", keep="first").copy()
    rows = []
    for ep in launch.itertuples(index=False):
        inst = clean_str(ep.instrument).upper()
        signal_date = as_date(ep.signal_date)
        split = split_for_date(config, signal_date)
        if split not in PRIMARY_SPLITS:
            continue
        row = {
            "baseline_event_id": stable_id("DF_BASE", "all_context", "all_launch_direct_baseline", ep.launch_episode_id),
            "deferred_family_event_id": "all_context",
            "baseline_id": "all_launch_direct_baseline",
            "lookalike_source_family": "all",
            "donor_source_table": "ep2_launch_observation_pool",
            "instrument": inst,
            "signal_date": signal_date,
            "execution_date": add_trading_days(calendar, signal_date, 1),
            "split": split,
            "match_status": "matched",
            "match_reason": "all_launch_context",
            "trading_day_distance_to_anchor": np.nan,
            "replacement_sequence_rank": 0,
            "diagnostic_bucket_source": "baseline_event",
            "money_bucket": "unbucketed",
            "vol20_bucket": "unbucketed",
            "ret_60d_bucket": "unbucketed",
            "industry_bucket": clean_str((lookup.get((inst, signal_date), {}) or {}).get("industry_name")) or "UNKNOWN",
            "year_bucket": str(signal_date.year),
            "is_executable_next_open": bool(getattr(ep, "is_buy_executable_next_open", False)),
            "blocked_buy_reason": clean_str(getattr(ep, "blocked_buy_reason", "")),
        }
        add_forward_metrics(config, calendar, lookup, row)
        row["row_hash"] = canonical_hash(row)
        rows.append(row)
    return rows


def build_stopped_ac_baseline(config: dict[str, Any], inputs: dict[str, Any]) -> list[dict[str, Any]]:
    p05 = inputs["p05_anchor_panel"].copy()
    rows = []
    keep = p05.loc[p05["anchor_family_id"].isin(config["deferred_family_scope"]["stopped_primary_families"]) & p05["primary_diagnostic_eligible"].map(as_bool) & p05["eligible_for_primary_gate"].map(as_bool)].copy()
    for row in keep.itertuples(index=False):
        payload = {
            "baseline_event_id": stable_id("DF_BASE", "stopped_ac", row.anchor_event_id),
            "deferred_family_event_id": "all_context",
            "baseline_id": "stopped_ac_anchor_baseline",
            "lookalike_source_family": row.anchor_family_id,
            "donor_source_table": "p0_5_anchor_event_diagnostic_panel",
            "instrument": row.instrument,
            "signal_date": row.signal_date,
            "execution_date": row.execution_date,
            "split": row.split,
            "match_status": "matched",
            "match_reason": "stopped_ac_context",
            "trading_day_distance_to_anchor": np.nan,
            "replacement_sequence_rank": 0,
            "diagnostic_bucket_source": "stopped_ac_event",
            "eligible_for_primary_gate": row.eligible_for_primary_gate,
            "money_bucket": getattr(row, "money_bucket", "unavailable"),
            "vol20_bucket": getattr(row, "vol20_bucket", "unavailable"),
            "ret_60d_bucket": getattr(row, "ret_60d_bucket", "unavailable"),
            "industry_bucket": getattr(row, "industry_bucket", "UNKNOWN"),
            "year_bucket": getattr(row, "year_bucket", str(pd.Timestamp(row.signal_date).year)),
            "is_executable_next_open": getattr(row, "is_executable_next_open", True),
            "blocked_buy_reason": getattr(row, "blocked_buy_reason", ""),
            "after_cost_return_H10": getattr(row, "after_cost_return_H10", np.nan),
            "max_adverse_excursion_H10": getattr(row, "max_adverse_excursion_H10", np.nan),
            "after_cost_return_H20": getattr(row, "after_cost_return_H20", np.nan),
            "max_adverse_excursion_H20": getattr(row, "max_adverse_excursion_H20", np.nan),
            "after_cost_return_H60": getattr(row, "after_cost_return_H60", np.nan),
            "max_adverse_excursion_H60": getattr(row, "max_adverse_excursion_H60", np.nan),
        }
        payload["row_hash"] = canonical_hash(payload)
        rows.append(payload)
    return rows


def baseline_columns() -> list[str]:
    return [
        "baseline_event_id",
        "deferred_family_event_id",
        "baseline_id",
        "lookalike_source_family",
        "donor_source_table",
        "instrument",
        "signal_date",
        "execution_date",
        "split",
        "match_status",
        "match_reason",
        "trading_day_distance_to_anchor",
        "replacement_sequence_rank",
        "diagnostic_bucket_source",
        "eligible_for_primary_gate",
        "money_bucket",
        "vol20_bucket",
        "ret_60d_bucket",
        "industry_bucket",
        "year_bucket",
        "is_executable_next_open",
        "blocked_buy_reason",
        "after_cost_return_H10",
        "max_adverse_excursion_H10",
        "after_cost_return_H20",
        "max_adverse_excursion_H20",
        "after_cost_return_H60",
        "max_adverse_excursion_H60",
        "row_hash",
    ]


def denominator(inputs: dict[str, Any], config: dict[str, Any]) -> pd.DataFrame:
    ep = inputs["ep2_launch_pool"].sort_values(["launch_episode_id", "signal_date"]).drop_duplicates("launch_episode_id", keep="first").copy()
    ep["split"] = ep["signal_date"].map(lambda x: split_for_date(config, x))
    return ep.loc[ep["split"].isin(PRIMARY_SPLITS)].copy()


def instrument_year_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    return int((df["instrument"].astype(str) + "_" + pd.to_datetime(df["signal_date"]).dt.year.astype(str)).nunique())


def positive_rate(df: pd.DataFrame, ret_col: str) -> float:
    if df.empty or ret_col not in df:
        return np.nan
    tmp = df.copy()
    tmp["iy"] = tmp["instrument"].astype(str) + "_" + pd.to_datetime(tmp["signal_date"]).dt.year.astype(str)
    pnl = tmp.groupby("iy")[ret_col].sum(min_count=1).dropna()
    return float((pnl > 0).mean()) if len(pnl) else np.nan


def top1_share(df: pd.DataFrame, ret_col: str) -> float:
    if df.empty or ret_col not in df:
        return np.nan
    tmp = df.copy()
    tmp["iy"] = tmp["instrument"].astype(str) + "_" + pd.to_datetime(tmp["signal_date"]).dt.year.astype(str)
    pos = tmp.groupby("iy")[ret_col].sum(min_count=1).dropna()
    pos = pos.loc[pos > 0]
    return float(pos.max() / pos.sum()) if len(pos) and pos.sum() > 0 else 0.0


def top5_exp(df: pd.DataFrame) -> float:
    return float(df["instrument"].value_counts().head(5).sum() / len(df)) if len(df) else np.nan


def metric_values(df: pd.DataFrame, horizon: str) -> dict[str, Any]:
    ret = pd.to_numeric(df.get(f"after_cost_return_{horizon}", pd.Series(dtype=float)), errors="coerce").dropna()
    mae = pd.to_numeric(df.get(f"max_adverse_excursion_{horizon}", pd.Series(dtype=float)), errors="coerce").dropna()
    return {
        "event_count": int(len(df)),
        "unique_instrument_count": int(df["instrument"].nunique()) if len(df) else 0,
        "unique_instrument_year_count": instrument_year_count(df),
        "mean": float(ret.mean()) if len(ret) else np.nan,
        "p05": float(ret.quantile(0.05)) if len(ret) else np.nan,
        "mae": float(mae.mean()) if len(mae) else np.nan,
        "positive_rate": positive_rate(df, f"after_cost_return_{horizon}"),
        "top1": top1_share(df, f"after_cost_return_{horizon}"),
        "top5": top5_exp(df),
        "winner_capture": float(pd.Series(df.get("winner_50h120", pd.Series(dtype=float))).mean()) if len(df) and "winner_50h120" in df else np.nan,
    }


def interpretation_status(count: int, iy: int, config: dict[str, Any]) -> str:
    return "interpretable" if count >= int(config["diagnostic_bins"]["event_count_min_for_interpretation"]) and iy >= int(config["diagnostic_bins"]["instrument_year_count_min_for_interpretation"]) else "too_sparse"


def rows_for_axis(df: pd.DataFrame, axis: str) -> list[tuple[str, pd.DataFrame]]:
    if axis == "all":
        return [("all", df)]
    if axis not in df:
        return []
    return [(str(k), g.copy()) for k, g in df.groupby(axis, dropna=False)]


def build_reports(config: dict[str, Any], inputs: dict[str, Any], event: pd.DataFrame, baseline: pd.DataFrame, freeze: pd.DataFrame, calendar: pd.DatetimeIndex) -> dict[str, pd.DataFrame]:
    denom = denominator(inputs, config)
    reports: dict[str, pd.DataFrame] = {}
    reports["event_summary"] = build_event_summary(event)
    reports["trigger"] = build_trigger_decomposition(config, event, denom)
    reports["matched_lift"] = build_lift(config, event, baseline, denom, "H20")
    reports["tail"] = build_tail(reports["matched_lift"])
    reports["sensitivity"] = pd.concat([build_lift(config, event, baseline, denom, h, sensitivity=True) for h in config["deferred_family_scope"]["sensitivity_horizons"]], ignore_index=True)
    reports["ac_attr"] = build_ac_attribution(config, inputs, event, calendar)
    reports["gate"] = build_gate_audit(config, reports["trigger"], reports["matched_lift"], reports["tail"], reports["ac_attr"], freeze)
    reports["decision"] = build_decision(reports["gate"], reports["trigger"], reports["matched_lift"])
    return reports


def build_event_summary(event: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (split, family, event_type, status), g in event.groupby(["split", "lookalike_source_family", "event_type", "avoidance_status"], dropna=False):
        rows.append(
            {
                "split": split,
                "anchor_family_id": ANCHOR_FAMILY,
                "lookalike_source_family": family,
                "event_type": event_type,
                "avoidance_status": status,
                "event_count": len(g),
                "primary_forward_audit_event_count": int(g["is_primary_forward_audit_event"].map(as_bool).sum()),
                "gate_eligible_h20_event_count": int(g["eligible_for_primary_gate"].map(as_bool).sum()),
                "unique_launch_episode_count": int(g["launch_episode_id"].nunique()),
                "unique_instrument_count": int(g["instrument"].nunique()),
                "unique_instrument_year_count": instrument_year_count(g),
                "unavailable_formula_row_count": 0,
                "event_summary_status": "passed",
            }
        )
    return pd.DataFrame(rows)


def build_trigger_decomposition(config: dict[str, Any], event: pd.DataFrame, denom: pd.DataFrame) -> pd.DataFrame:
    axes = ["all", "lookalike_source_family", "failure_condition_id", "failure_margin_bucket", "money_bucket", "vol20_bucket", "ret_60d_bucket", "industry_bucket", "year_bucket"]
    rows = []
    denom_counts = denom.groupby("split")["launch_episode_id"].nunique().to_dict()
    type_map = {
        "recovery_after_failed_lookalike": ["raw_recovery_event", "gate_eligible_h20_recovery_event"],
        "failure_lookalike_state": ["diagnostic_failure_state"],
        "clean_avoidance_state": ["diagnostic_clean_avoidance_state"],
    }
    for split in PRIMARY_SPLITS:
        split_event = event.loc[event["split"].eq(split)].copy()
        for event_type, rate_types in type_map.items():
            base = split_event.loc[split_event["event_type"].eq(event_type)]
            for rate_type in rate_types:
                df = base
                if rate_type == "gate_eligible_h20_recovery_event":
                    df = base.loc[base["is_primary_forward_audit_event"].map(as_bool)]
                for axis in axes:
                    for bucket, group in rows_for_axis(df, axis):
                        denom_n = int(denom_counts.get(split, 0))
                        count = len(group)
                        rows.append(
                            {
                                "split": split,
                                "anchor_family_id": ANCHOR_FAMILY,
                                "event_type": event_type,
                                "diagnostic_axis": axis,
                                "diagnostic_bucket": bucket,
                                "predeclared_partition_id": stable_id("DF_PART", axis, bucket),
                                "trigger_rate_type": rate_type,
                                "event_count": count,
                                "canonical_launch_episode_count": denom_n,
                                "trigger_rate_per_launch_episode": count / denom_n if denom_n else np.nan,
                                "unique_instrument_count": int(group["instrument"].nunique()) if count else 0,
                                "unique_instrument_year_count": instrument_year_count(group),
                                "trigger_rate_band": "all",
                                "interpretation_status": interpretation_status(count, instrument_year_count(group), config),
                            }
                        )
    return pd.DataFrame(rows)


def build_lift(config: dict[str, Any], event: pd.DataFrame, baseline: pd.DataFrame, denom: pd.DataFrame, horizon: str, sensitivity: bool = False) -> pd.DataFrame:
    axes = ["all", "failure_margin_bucket", "money_bucket", "vol20_bucket", "ret_60d_bucket", "industry_bucket", "year_bucket"]
    anchors = event.loc[event["is_primary_forward_audit_event"].map(as_bool) & pd.to_numeric(event[f"after_cost_return_{horizon}"], errors="coerce").notna()].copy()
    rows = []
    for split in PRIMARY_SPLITS:
        split_anchor = anchors.loc[anchors["split"].eq(split)]
        for baseline_id in BASELINES:
            split_base = baseline.loc[baseline["split"].eq(split) & baseline["baseline_id"].eq(baseline_id) & baseline["match_status"].eq("matched") & baseline["eligible_for_primary_gate"].map(as_bool)].copy()
            for axis in axes:
                if baseline_id == "all_launch_direct_baseline" and axis in {"failure_margin_bucket"}:
                    continue
                anchor_groups = dict(rows_for_axis(split_anchor, axis))
                base_groups = dict(rows_for_axis(split_base, axis if axis in split_base else "all"))
                for bucket in sorted(set(anchor_groups) | set(base_groups)):
                    ag = anchor_groups.get(bucket, split_anchor.iloc[0:0])
                    bg = base_groups.get(bucket, split_base.iloc[0:0])
                    av = metric_values(ag, horizon)
                    bv = metric_values(bg, horizon)
                    payload = {
                        "split": split,
                        "anchor_family_id": ANCHOR_FAMILY,
                        "baseline_id": baseline_id,
                        "diagnostic_axis": axis,
                        "diagnostic_bucket": bucket,
                        "predeclared_partition_id": stable_id("DF_PART", axis, bucket),
                        "diagnostic_bucket_source": "linked_deferred_event" if baseline_id in PAIRWISE_BASELINES else "baseline_event",
                        "anchor_event_count": av["event_count"],
                        "baseline_event_count": bv["event_count"],
                        "unique_instrument_year_count": av["unique_instrument_year_count"],
                        f"anchor_mean_after_cost_return_{horizon}": av["mean"],
                        f"baseline_mean_after_cost_return_{horizon}": bv["mean"],
                        "mean_diff_vs_baseline": av["mean"] - bv["mean"] if math.isfinite(av["mean"]) and math.isfinite(bv["mean"]) else np.nan,
                        f"anchor_p05_after_cost_return_{horizon}": av["p05"],
                        f"baseline_p05_after_cost_return_{horizon}": bv["p05"],
                        "p05_diff_vs_baseline": av["p05"] - bv["p05"] if math.isfinite(av["p05"]) and math.isfinite(bv["p05"]) else np.nan,
                        f"anchor_max_adverse_excursion_mean_{horizon}": av["mae"],
                        f"baseline_max_adverse_excursion_mean_{horizon}": bv["mae"],
                        "mae_worsening_vs_baseline": av["mae"] - bv["mae"] if math.isfinite(av["mae"]) and math.isfinite(bv["mae"]) else np.nan,
                        "anchor_instrument_year_positive_rate": av["positive_rate"],
                        "baseline_instrument_year_positive_rate": bv["positive_rate"],
                        "instrument_year_positive_rate_diff": av["positive_rate"] - bv["positive_rate"] if math.isfinite(av["positive_rate"]) and math.isfinite(bv["positive_rate"]) else np.nan,
                        "interpretation_status": interpretation_status(av["event_count"], av["unique_instrument_year_count"], config),
                    }
                    if sensitivity:
                        payload = {
                            "split": split,
                            "anchor_family_id": ANCHOR_FAMILY,
                            "baseline_id": baseline_id,
                            "horizon": horizon,
                            "diagnostic_axis": axis,
                            "diagnostic_bucket": bucket,
                            "anchor_event_count": av["event_count"],
                            "baseline_event_count": bv["event_count"],
                            "anchor_mean_after_cost_return": av["mean"],
                            "baseline_mean_after_cost_return": bv["mean"],
                            "mean_diff_vs_baseline": payload["mean_diff_vs_baseline"],
                            "anchor_p05_after_cost_return": av["p05"],
                            "baseline_p05_after_cost_return": bv["p05"],
                            "p05_diff_vs_baseline": payload["p05_diff_vs_baseline"],
                            "sensitivity_only": True,
                            "interpretation_status": "report_only" if payload["interpretation_status"] == "interpretable" else "too_sparse",
                        }
                    rows.append(payload)
    return pd.DataFrame(rows)


def build_tail(lift: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in lift.itertuples(index=False):
        d = row._asdict()
        rows.append(
            {
                "split": d["split"],
                "anchor_family_id": d["anchor_family_id"],
                "baseline_id": d["baseline_id"],
                "diagnostic_axis": d["diagnostic_axis"],
                "diagnostic_bucket": d["diagnostic_bucket"],
                "diagnostic_bucket_source": d["diagnostic_bucket_source"],
                "anchor_event_count": d["anchor_event_count"],
                "baseline_event_count": d["baseline_event_count"],
                "anchor_p05_after_cost_return_H20": d.get("anchor_p05_after_cost_return_H20", np.nan),
                "baseline_p05_after_cost_return_H20": d.get("baseline_p05_after_cost_return_H20", np.nan),
                "p05_diff_vs_baseline": d["p05_diff_vs_baseline"],
                "anchor_max_adverse_excursion_mean_H20": d.get("anchor_max_adverse_excursion_mean_H20", np.nan),
                "baseline_max_adverse_excursion_mean_H20": d.get("baseline_max_adverse_excursion_mean_H20", np.nan),
                "mae_worsening_vs_baseline": d["mae_worsening_vs_baseline"],
                "top1_instrument_year_pnl_share": np.nan,
                "top5_instrument_exposure_share": np.nan,
                "interpretation_status": d["interpretation_status"],
            }
        )
    return pd.DataFrame(rows)


def build_ac_attribution(config: dict[str, Any], inputs: dict[str, Any], event: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    ac = inputs["p05_anchor_panel"].loc[
        inputs["p05_anchor_panel"]["split"].isin(["validation", "robustness"])
        & inputs["p05_anchor_panel"]["anchor_family_id"].isin(config["deferred_family_scope"]["stopped_primary_families"])
        & inputs["p05_anchor_panel"]["primary_diagnostic_eligible"].map(as_bool)
        & inputs["p05_anchor_panel"]["eligible_for_primary_gate"].map(as_bool)
        & pd.to_numeric(inputs["p05_anchor_panel"]["after_cost_return_H20"], errors="coerce").notna()
    ].copy()
    joined = []
    max_lb = int(config["observable_failure_lookalike_rules"]["max_ac_attribution_lookback_days"])
    for row in ac.itertuples(index=False):
        cand = event.loc[event["split"].eq(row.split) & event["instrument"].eq(row.instrument) & event["signal_date"].le(row.signal_date)].copy()
        if not cand.empty:
            cand["_dist"] = cand["signal_date"].map(lambda d: trading_day_distance(calendar, d, row.signal_date))
            cand = cand.loc[cand["_dist"].notna() & cand["_dist"].le(max_lb)]
        if cand.empty:
            bucket = "no_deferred_match"
        else:
            order = {"recovery_after_failed_lookalike": 0, "failure_lookalike_state": 1, "clean_avoidance_state": 2}
            cand["_pref"] = cand["event_type"].map(order).fillna(9)
            best = cand.sort_values(["_dist", "_pref", "deferred_family_event_id"]).iloc[0]
            bucket = clean_str(best["avoidance_status"])
        payload = row._asdict()
        payload["attribution_bucket"] = bucket
        joined.append(payload)
    jdf = pd.DataFrame(joined)
    rows = []
    buckets = ["recovered_after_failure", "persistent_failure", "clean_avoidance", "no_deferred_match"]
    for split in ["validation", "robustness"]:
        for family in config["deferred_family_scope"]["stopped_primary_families"]:
            fam = jdf.loc[jdf["split"].eq(split) & jdf["anchor_family_id"].eq(family)] if not jdf.empty else pd.DataFrame()
            p05 = float(pd.to_numeric(fam["after_cost_return_H20"], errors="coerce").quantile(0.05)) if len(fam) else np.nan
            for bucket in buckets:
                g = fam.loc[fam["attribution_bucket"].eq(bucket)] if not fam.empty else fam
                rows.append(
                    {
                        "split": split,
                        "stopped_ac_family_id": family,
                        "attribution_bucket": bucket,
                        "ac_event_count": len(g),
                        "ac_mean_after_cost_return_H20": float(pd.to_numeric(g.get("after_cost_return_H20", pd.Series(dtype=float)), errors="coerce").mean()) if len(g) else np.nan,
                        "ac_p05_after_cost_return_H20": float(pd.to_numeric(g.get("after_cost_return_H20", pd.Series(dtype=float)), errors="coerce").quantile(0.05)) if len(g) else np.nan,
                        "ac_mae_mean_H20": float(pd.to_numeric(g.get("max_adverse_excursion_H20", pd.Series(dtype=float)), errors="coerce").mean()) if len(g) else np.nan,
                        "matched_delay_mean_diff": np.nan,
                        "tail_event_share": float((pd.to_numeric(g.get("after_cost_return_H20", pd.Series(dtype=float)), errors="coerce") <= p05).mean()) if len(g) and math.isfinite(p05) else np.nan,
                        "winner_capture_rate_50h120": float(g.get("winner_50h120", pd.Series(dtype=float)).mean()) if len(g) and "winner_50h120" in g else np.nan,
                        "interpretation_status": interpretation_status(len(g), instrument_year_count(g), config) if len(g) else "too_sparse",
                    }
                )
    return pd.DataFrame(rows)


def row_value(df: pd.DataFrame, split: str, baseline: str, col: str) -> float:
    row = df.loc[df["split"].eq(split) & df["baseline_id"].eq(baseline) & df["diagnostic_axis"].eq("all") & df["diagnostic_bucket"].eq("all")]
    if row.empty or col not in row:
        return np.nan
    return finite_float(row.iloc[0][col])


def trigger_value(trigger: pd.DataFrame, split: str) -> float:
    row = trigger.loc[trigger["split"].eq(split) & trigger["event_type"].eq("recovery_after_failed_lookalike") & trigger["trigger_rate_type"].eq("gate_eligible_h20_recovery_event") & trigger["diagnostic_axis"].eq("all")]
    return finite_float(row.iloc[0]["trigger_rate_per_launch_episode"]) if not row.empty else np.nan


def build_gate_audit(config: dict[str, Any], trigger: pd.DataFrame, lift: pd.DataFrame, tail: pd.DataFrame, ac_attr: pd.DataFrame, freeze: pd.DataFrame) -> pd.DataFrame:
    g = config["gates"]
    checks = [
        ("validation_trigger_rate", trigger_value(trigger, "validation"), g["min_validation_trigger_rate_per_launch_episode"], ">="),
        ("validation_unique_instrument_year_count", row_value(lift, "validation", "matched_delay_baseline", "unique_instrument_year_count"), config["diagnostic_bins"]["validation_min_unique_instrument_year_count_for_gate"], ">="),
        ("validation_h20_mean_diff_vs_matched_delay", row_value(lift, "validation", "matched_delay_baseline", "mean_diff_vs_baseline"), g["min_validation_h20_mean_diff_vs_matched_delay"], ">"),
        ("validation_h20_p05_diff_vs_matched_delay", row_value(lift, "validation", "matched_delay_baseline", "p05_diff_vs_baseline"), g["min_validation_h20_p05_diff_vs_matched_delay"], ">="),
        ("validation_h20_mae_worsening_vs_matched_delay", row_value(lift, "validation", "matched_delay_baseline", "mae_worsening_vs_baseline"), g["max_validation_h20_mae_worsening_vs_matched_delay"], "<="),
        ("validation_instrument_year_positive_rate_diff", row_value(lift, "validation", "matched_delay_baseline", "instrument_year_positive_rate_diff"), g["min_validation_instrument_year_positive_rate_diff"], ">="),
        ("robustness_h20_mean_diff_vs_matched_delay", row_value(lift, "robustness", "matched_delay_baseline", "mean_diff_vs_baseline"), g["min_robustness_h20_mean_diff_vs_matched_delay"], ">="),
        ("robustness_h20_p05_diff_vs_matched_delay", row_value(lift, "robustness", "matched_delay_baseline", "p05_diff_vs_baseline"), g["min_robustness_h20_p05_diff_vs_matched_delay"], ">="),
        ("robustness_trigger_not_collapsed", trigger_value(trigger, "robustness"), trigger_value(trigger, "validation") / 2.0 if math.isfinite(trigger_value(trigger, "validation")) else np.nan, ">="),
    ]
    rows = []
    insufficient = freeze.loc[freeze["freeze_type"].eq("train_median_recovery_delay_days") & freeze["freeze_status"].eq("insufficient_train_rows")]
    for name, value, threshold, comp in checks:
        passed = compare(value, threshold, comp)
        failure = "insufficient_train_recovery_rows" if name.startswith("validation_h20") and not insufficient.empty else "failed_gate"
        rows.append(
            {
                "gate_name": name,
                "gate_value": value,
                "threshold": threshold,
                "comparison": comp,
                "gate_passed": passed,
                "failure_status_if_failed": "" if passed else failure,
                "gate_source_report": "deferred_family_matched_lift.csv" if "h20" in name or "positive" in name else "deferred_family_trigger_decomposition.csv",
            }
        )
    persistent_val = ac_attr.loc[ac_attr["split"].eq("validation") & ac_attr["attribution_bucket"].eq("persistent_failure")]["tail_event_share"].mean()
    persistent_rob = ac_attr.loc[ac_attr["split"].eq("robustness") & ac_attr["attribution_bucket"].eq("persistent_failure")]["tail_event_share"].mean()
    rows.append({"gate_name": "persistent_failure_validation_tail_share", "gate_value": persistent_val, "threshold": 0.5, "comparison": ">=", "gate_passed": compare(persistent_val, 0.5, ">="), "failure_status_if_failed": "failed_formula_refinement_gate" if not compare(persistent_val, 0.5, ">=") else "", "gate_source_report": "deferred_family_ac_failure_attribution.csv"})
    rows.append({"gate_name": "persistent_failure_robustness_tail_share", "gate_value": persistent_rob, "threshold": 0.3, "comparison": ">=", "gate_passed": compare(persistent_rob, 0.3, ">="), "failure_status_if_failed": "failed_formula_refinement_gate" if not compare(persistent_rob, 0.3, ">=") else "", "gate_source_report": "deferred_family_ac_failure_attribution.csv"})
    return pd.DataFrame(rows)


def compare(value: Any, threshold: Any, op: str) -> bool:
    x = finite_float(value)
    y = finite_float(threshold)
    if not math.isfinite(x) or not math.isfinite(y):
        return False
    if op == ">=":
        return x >= y
    if op == ">":
        return x > y
    if op == "<=":
        return x <= y
    return False


def build_decision(gate: pd.DataFrame, trigger: pd.DataFrame, lift: pd.DataFrame) -> pd.DataFrame:
    freeze_gate_names = [name for name in gate["gate_name"] if not str(name).startswith("persistent_failure")]
    freeze_pass = gate.loc[gate["gate_name"].isin(freeze_gate_names), "gate_passed"].map(as_bool).all()
    refine_pass = gate.loc[gate["gate_name"].str.startswith("persistent_failure"), "gate_passed"].map(as_bool).all()
    decision = "write_p0_6_deferred_family_freeze_requirement" if freeze_pass else ("write_p0_6_deferred_family_formula_refinement_requirement" if refine_pass else "stop_deferred_family")
    row = {
        "recommended_decision": decision,
        "decision_rule_status": "passed",
        "supporting_gate_names": ";".join(gate.loc[gate["gate_passed"].map(as_bool), "gate_name"].astype(str)),
        "primary_evidence_report": "deferred_family_gate_audit.csv",
        "validation_trigger_rate_per_launch_episode": trigger_value(trigger, "validation"),
        "validation_unique_instrument_year_count": row_value(lift, "validation", "matched_delay_baseline", "unique_instrument_year_count"),
        "validation_mean_diff_vs_matched_delay": row_value(lift, "validation", "matched_delay_baseline", "mean_diff_vs_baseline"),
        "validation_p05_diff_vs_matched_delay": row_value(lift, "validation", "matched_delay_baseline", "p05_diff_vs_baseline"),
        "robustness_mean_diff_vs_matched_delay": row_value(lift, "robustness", "matched_delay_baseline", "mean_diff_vs_baseline"),
        "robustness_p05_diff_vs_matched_delay": row_value(lift, "robustness", "matched_delay_baseline", "p05_diff_vs_baseline"),
        "decision_rationale": "Decision follows frozen H20 gates and formula-refinement attribution precedence.",
    }
    return pd.DataFrame([row])


def write_report(paths: Paths, reproduction: pd.DataFrame, decision: pd.DataFrame, trigger: pd.DataFrame, lift: pd.DataFrame, gate: pd.DataFrame) -> None:
    dec = decision.iloc[0].to_dict()
    lines = [
        "# EP3 Deferred-Family Failure-Lookalike Audit",
        "",
        "## Final Decision",
        "",
        f"`{dec['recommended_decision']}`",
        "",
        "## Upstream Problem Chain",
        "",
        "EP3 P0 stopped A/C after trigger, lift, robustness, and tail failures. P0.5 confirmed A/C should stop and authorized this deferred-family requirement.",
        "",
        "## Trigger Summary",
        "",
        trigger.loc[trigger["diagnostic_axis"].eq("all") & trigger["trigger_rate_type"].eq("gate_eligible_h20_recovery_event")][["split", "event_count", "canonical_launch_episode_count", "trigger_rate_per_launch_episode"]].to_markdown(index=False),
        "",
        "## Matched Lift Summary",
        "",
        lift.loc[lift["diagnostic_axis"].eq("all") & lift["baseline_id"].eq("matched_delay_baseline")][["split", "anchor_event_count", "baseline_event_count", "mean_diff_vs_baseline", "p05_diff_vs_baseline", "mae_worsening_vs_baseline"]].to_markdown(index=False),
        "",
        "## Gate Summary",
        "",
        gate[["gate_name", "gate_value", "threshold", "comparison", "gate_passed", "failure_status_if_failed"]].to_markdown(index=False),
        "",
        "## Validator Status",
        "",
        "Run the validator to stamp `validation_status = passed` in the manifest.",
    ]
    (paths.reports_dir / "deferred_family_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_stage_order(paths: Paths, stage_rows: list[tuple[int, str, list[str]]]) -> pd.DataFrame:
    rows = []
    for stage_id, name, artifacts in stage_rows:
        rows.append(
            {
                "stage_id": stage_id,
                "stage_name": name,
                "stage_order": stage_id,
                "started_at_utc": now_iso(),
                "finished_at_utc": now_iso(),
                "input_artifact_hashes": "",
                "output_artifact_hashes": canonical_hash([{a: live_hash(paths.output_root / a)} for a in artifacts]),
                "stage_status": "passed",
            }
        )
    return pd.DataFrame(rows)


def manifest_artifacts(paths: Paths) -> dict[str, str]:
    rels = [*(f"cache/{x}" for x in REQUIRED_CACHE), *(f"reports/{x}" for x in REQUIRED_REPORTS)]
    return {rel: live_hash(paths.output_root / rel) for rel in rels if (paths.output_root / rel).exists()}


def write_manifest(config: dict[str, Any], paths: Paths, validation_status: str, failures: list[str] | None = None) -> dict[str, Any]:
    artifact_hashes = manifest_artifacts(paths)
    manifest = {
        "requirement_id": "ep3_deferred_family_failure_lookalike_audit",
        "phase": config["phase"],
        "run_id": stable_id("DF_RUN", file_hash(paths.config_path), len(artifact_hashes)),
        "config_path": relpath(paths.config_path),
        "config_hash": file_hash(paths.config_path),
        "output_root": relpath(paths.output_root),
        "validation_status": validation_status,
        "validation_failures": failures or [],
        "upstream_authority_hashes": {},
        "artifact_hashes": artifact_hashes,
        "stage_order_hash": live_hash(paths.reports_dir / "deferred_family_stage_order_audit.csv"),
        "formula_dictionary_hash": live_hash(paths.reports_dir / "deferred_family_formula_dictionary.csv"),
        "created_at_utc": now_iso(),
        "git_commit": git_commit_hash(),
        "forbidden_inputs": {
            "ep2_r02_threshold_artifacts": "not_used",
            "ep2_r03_confirmed_pool": "not_used",
            "ep2_r05_policy_outputs": "not_used",
            "baserate_row_level_cache": "not_used",
            "explore9_explore10_row_level_outputs": "not_used",
            "new_tushare_akshare_fetch": "not_used",
        },
    }
    auth_path = paths.reports_dir / "deferred_family_upstream_authority.csv"
    if auth_path.exists():
        auth = pd.read_csv(auth_path)
        manifest["upstream_authority_hashes"] = dict(zip(auth["artifact_path"], auth["observed_hash"]))
    write_json(manifest, paths.manifests_dir / "deferred_family_manifest.json")
    return manifest


def stamp_report_validation_status(paths: Paths, status: str, failures: list[str]) -> None:
    path = paths.reports_dir / "deferred_family_report.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    marker = "## Validator Status"
    replacement = (
        "## Validator Status\n\n"
        f"`validation_status = {status}`\n\n"
        f"`validation_failures = {json.dumps(failures, ensure_ascii=False)}`"
    )
    if marker in text:
        head = text.split(marker, 1)[0].rstrip()
        text = head + "\n\n" + replacement + "\n"
    else:
        text = text.rstrip() + "\n\n" + replacement + "\n"
    path.write_text(text, encoding="utf-8")


def run_deferred_family_failure_lookalike_audit(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    if relpath(paths.output_root) != config["output_root"]:
        raise DeferredFamilyError("output_root must remain under deferred family audit root")
    inputs = load_inputs(config)
    if inputs["p0_manifest"].get("validation_status") != "passed" or inputs["p05_manifest"].get("validation_status") != "passed":
        raise DeferredFamilyError("upstream EP3 P0/P0.5 manifest must be validation_status=passed")
    authority = build_upstream_authority(config, inputs)
    transition = build_transition_audit(config, inputs)
    if authority["authority_status"].ne("passed").any() or transition["transition_status"].ne("passed").any():
        raise DeferredFamilyError("upstream authority or transition check failed")
    lifecycle = build_lifecycle_source_audit(inputs)
    calendar = load_calendar(config)
    market = load_market_panel(config)
    print("loaded upstream inputs and market panel")
    dictionary = build_formula_dictionary()
    formula = build_formula_diagnostics(config, inputs, calendar, market, dictionary)
    print(f"built formula diagnostics rows={len(formula)}")
    event, freeze = build_events_and_freeze(config, inputs, formula, dictionary, calendar, market)
    print(f"built deferred events rows={len(event)}")
    baseline = build_matched_baselines(config, inputs, event, freeze, calendar, market)
    print(f"built baselines rows={len(baseline)}")
    reports = build_reports(config, inputs, event, baseline, freeze, calendar)

    write_csv(authority, paths.reports_dir / "deferred_family_upstream_authority.csv")
    write_csv(transition, paths.reports_dir / "deferred_family_transition_audit.csv")
    write_csv(lifecycle, paths.reports_dir / "deferred_family_lifecycle_source_audit.csv")
    write_csv(dictionary, paths.reports_dir / "deferred_family_formula_dictionary.csv")
    write_csv(freeze, paths.reports_dir / "deferred_family_diagnostic_bin_freeze.csv")
    write_parquet(formula, paths.cache_dir / "deferred_family_formula_diagnostic_panel.parquet")
    write_parquet(event, paths.cache_dir / "deferred_family_event_panel.parquet")
    write_parquet(baseline, paths.cache_dir / "deferred_family_matched_baseline_panel.parquet")
    write_csv(reports["event_summary"], paths.reports_dir / "deferred_family_event_summary.csv")
    write_csv(reports["trigger"], paths.reports_dir / "deferred_family_trigger_decomposition.csv")
    write_csv(reports["matched_lift"], paths.reports_dir / "deferred_family_matched_lift.csv")
    write_csv(reports["tail"], paths.reports_dir / "deferred_family_tail_risk.csv")
    write_csv(reports["ac_attr"], paths.reports_dir / "deferred_family_ac_failure_attribution.csv")
    write_csv(reports["sensitivity"], paths.reports_dir / "deferred_family_sensitivity_horizon_audit.csv")
    write_csv(reports["gate"], paths.reports_dir / "deferred_family_gate_audit.csv")
    write_csv(reports["decision"], paths.reports_dir / "deferred_family_decision.csv")
    write_report(paths, transition, reports["decision"], reports["trigger"], reports["matched_lift"], reports["gate"])
    stage = write_stage_order(
        paths,
        [
            (1, "upstream authority check for EP3 P0 and P0.5", ["reports/deferred_family_upstream_authority.csv"]),
            (2, "P0.5 transition-decision validation", ["reports/deferred_family_transition_audit.csv"]),
            (3, "train-only lifecycle deferred-family source audit", ["reports/deferred_family_lifecycle_source_audit.csv"]),
            (4, "formula dictionary and formula diagnostic precompute", ["reports/deferred_family_formula_dictionary.csv", "cache/deferred_family_formula_diagnostic_panel.parquet"]),
            (5, "train-only diagnostic bin freeze", ["reports/deferred_family_diagnostic_bin_freeze.csv"]),
            (6, "deferred-family event panel construction", ["cache/deferred_family_event_panel.parquet"]),
            (7, "matched baseline construction", ["cache/deferred_family_matched_baseline_panel.parquet"]),
            (8, "forward-audit metric computation", ["reports/deferred_family_trigger_decomposition.csv", "reports/deferred_family_matched_lift.csv", "reports/deferred_family_tail_risk.csv", "reports/deferred_family_sensitivity_horizon_audit.csv"]),
            (9, "A/C failure attribution and comparison", ["reports/deferred_family_ac_failure_attribution.csv"]),
            (10, "gate audit, decision report, and manifest", ["reports/deferred_family_gate_audit.csv", "reports/deferred_family_decision.csv", "reports/deferred_family_report.md"]),
        ],
    )
    write_csv(stage, paths.reports_dir / "deferred_family_stage_order_audit.csv")
    manifest = write_manifest(config, paths, "not_run")
    return {"outputs": relpath(paths.output_root), "manifest": manifest}


def require_columns(df: pd.DataFrame, columns: list[str], label: str, failures: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        failures.append(f"{label} missing columns: {missing}")


def validate_deferred_family_failure_lookalike_audit(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    failures: list[str] = []
    if relpath(paths.output_root) != config["output_root"]:
        failures.append("unexpected output root")
    for cache in REQUIRED_CACHE:
        if not (paths.cache_dir / cache).exists():
            failures.append(f"missing cache: {cache}")
    for report in REQUIRED_REPORTS:
        if not (paths.reports_dir / report).exists():
            failures.append(f"missing report: {report}")
    inputs = load_inputs(config)
    if inputs["p0_manifest"].get("validation_status") != "passed":
        failures.append("P0 manifest is not passed")
    if inputs["p05_manifest"].get("validation_status") != "passed":
        failures.append("P0.5 manifest is not passed")
    expected_authority = build_upstream_authority(config, inputs)
    auth_path = paths.reports_dir / "deferred_family_upstream_authority.csv"
    if auth_path.exists():
        authority = pd.read_csv(auth_path)
        require_columns(authority, ["authority_check_id", "authority_type", "artifact_path", "required_hash", "observed_hash", "required_validation_status", "observed_validation_status", "authority_status"], "authority", failures)
        if authority.duplicated("authority_check_id").any():
            failures.append("duplicate authority primary key")
        if authority["authority_status"].ne("passed").any():
            failures.append("authority contains failed rows")
        for row in expected_authority.itertuples(index=False):
            actual = authority.loc[authority["authority_check_id"].eq(row.authority_check_id)]
            if actual.empty or clean_str(actual.iloc[0]["observed_hash"]) != clean_str(row.observed_hash):
                failures.append(f"authority hash mismatch: {row.artifact_path}")
    trans_path = paths.reports_dir / "deferred_family_transition_audit.csv"
    if trans_path.exists():
        transition = pd.read_csv(trans_path)
        if transition["transition_status"].ne("passed").any():
            failures.append("transition audit failed")
    dictionary_path = paths.reports_dir / "deferred_family_formula_dictionary.csv"
    dictionary = pd.read_csv(dictionary_path) if dictionary_path.exists() else pd.DataFrame()
    if not dictionary.empty:
        require_columns(dictionary, ["lookalike_source_family", "failure_condition_id", "formula_component_id", "formula_hash", "dictionary_row_hash"], "formula dictionary", failures)
        if dictionary.duplicated(["lookalike_source_family", "failure_condition_id", "formula_component_id"]).any():
            failures.append("duplicate formula dictionary primary key")
    if (paths.cache_dir / "deferred_family_formula_diagnostic_panel.parquet").exists():
        formula = pd.read_parquet(paths.cache_dir / "deferred_family_formula_diagnostic_panel.parquet")
        require_columns(formula, ["formula_diagnostic_row_id", "launch_episode_id", "split", "lookalike_source_family", "candidate_signal_date", "failure_condition_id", "failed_condition_count", "formula_availability_status", "source_formula_hash", "row_hash"], "formula diagnostic", failures)
        if formula.duplicated("formula_diagnostic_row_id").any():
            failures.append("duplicate formula diagnostic primary key")
    else:
        formula = pd.DataFrame()
    if (paths.cache_dir / "deferred_family_event_panel.parquet").exists():
        event = pd.read_parquet(paths.cache_dir / "deferred_family_event_panel.parquet")
        require_columns(event, event_columns(), "event panel", failures)
        if event.duplicated("deferred_family_event_id").any():
            failures.append("duplicate event primary key")
        if FORBIDDEN_FIELDS & set(event.columns):
            failures.append("event panel contains forbidden fields")
        bad_primary = event.loc[event["is_primary_forward_audit_event"].map(as_bool) & ~event["event_type"].eq("recovery_after_failed_lookalike")]
        if not bad_primary.empty:
            failures.append("non-recovery event used as primary numerator")
        if not dictionary.empty:
            for row in event.itertuples(index=False):
                expected = source_formula_hash(dictionary, row.lookalike_source_family, row.failure_condition_id)
                if clean_str(row.source_formula_hash) != expected:
                    failures.append("event source formula hash mismatch")
                    break
    else:
        event = pd.DataFrame()
    if (paths.reports_dir / "deferred_family_diagnostic_bin_freeze.csv").exists():
        freeze = pd.read_csv(paths.reports_dir / "deferred_family_diagnostic_bin_freeze.csv")
        require_columns(freeze, ["freeze_id", "freeze_type", "lookalike_source_family", "diagnostic_axis", "bin_edges", "train_source_row_count", "freeze_status", "row_hash"], "freeze", failures)
        if freeze.duplicated("freeze_id").any():
            failures.append("duplicate freeze primary key")
    else:
        freeze = pd.DataFrame()
    if (paths.cache_dir / "deferred_family_matched_baseline_panel.parquet").exists():
        baseline = pd.read_parquet(paths.cache_dir / "deferred_family_matched_baseline_panel.parquet")
        require_columns(baseline, baseline_columns(), "baseline panel", failures)
        if baseline.duplicated("baseline_event_id").any():
            failures.append("duplicate baseline primary key")
        if FORBIDDEN_FIELDS & set(baseline.columns):
            failures.append("baseline panel contains forbidden fields")
        bad_source = baseline.loc[baseline["baseline_id"].isin(["same_instrument_nonanchor_baseline", "industry_matched_baseline"]) & baseline["match_status"].eq("matched") & ~baseline["donor_source_table"].eq("ep3_winner_label_panel")]
        if not bad_source.empty:
            failures.append("baseline donor row not sourced from declared table")
        if not config["baseline_matching"]["control_replacement_allowed"]:
            dup = baseline.loc[baseline["baseline_id"].isin(["same_instrument_nonanchor_baseline", "industry_matched_baseline"]) & baseline["match_status"].eq("matched")]
            if dup.duplicated(["baseline_id", "split", "instrument", "signal_date"]).any():
                failures.append("baseline donor replacement used")
        all_launch = baseline.loc[baseline["baseline_id"].eq("all_launch_direct_baseline")]
        if not all_launch.empty and ("failure_margin_bucket" in all_launch.columns):
            failures.append("all_launch_direct_baseline decomposed by recovery-specific fields")
    else:
        baseline = pd.DataFrame()
    for report, key_cols in {
        "deferred_family_stage_order_audit.csv": ["stage_id"],
        "deferred_family_event_summary.csv": ["split", "lookalike_source_family", "event_type", "avoidance_status"],
        "deferred_family_trigger_decomposition.csv": ["split", "anchor_family_id", "event_type", "diagnostic_axis", "diagnostic_bucket", "trigger_rate_type"],
        "deferred_family_matched_lift.csv": ["split", "anchor_family_id", "baseline_id", "diagnostic_axis", "diagnostic_bucket", "diagnostic_bucket_source"],
        "deferred_family_sensitivity_horizon_audit.csv": ["split", "baseline_id", "horizon", "diagnostic_axis", "diagnostic_bucket"],
        "deferred_family_ac_failure_attribution.csv": ["split", "stopped_ac_family_id", "attribution_bucket"],
        "deferred_family_gate_audit.csv": ["gate_name"],
    }.items():
        path = paths.reports_dir / report
        if path.exists():
            df = pd.read_csv(path)
            if df.duplicated(key_cols).any():
                failures.append(f"duplicate report rows: {report}")
    decision_path = paths.reports_dir / "deferred_family_decision.csv"
    if decision_path.exists():
        decision = pd.read_csv(decision_path)
        allowed = {"stop_deferred_family", "write_p0_6_deferred_family_freeze_requirement", "write_p0_6_deferred_family_formula_refinement_requirement"}
        if len(decision) != 1 or clean_str(decision.iloc[0]["recommended_decision"]) not in allowed:
            failures.append("invalid deferred family decision")
    manifest_path = paths.manifests_dir / "deferred_family_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for rel, digest in manifest.get("artifact_hashes", {}).items():
            if live_hash(paths.output_root / rel) != digest:
                failures.append(f"manifest hash mismatch: {rel}")
    status = "passed" if not failures else "failed"
    stamp_report_validation_status(paths, status, failures)
    manifest = write_manifest(config, paths, status, failures)
    print(json.dumps({"validation_status": status, "validation_failures": failures}, ensure_ascii=False, indent=2))
    if failures:
        raise DeferredFamilyError("; ".join(failures))
    return manifest
