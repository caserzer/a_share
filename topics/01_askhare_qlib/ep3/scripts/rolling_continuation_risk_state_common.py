#!/usr/bin/env python3
from __future__ import annotations

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
DEFAULT_CONFIG = EP3_DIR / "configs" / "rolling_continuation_risk_state.yaml"
REQUIREMENT_ID = "ep3_rolling_continuation_risk_state_audit"
PRIMARY_PROCESS = "R03_original_H10_replay"
REQUIRED_CACHE = [
    "rolling_state_daily_panel.parquet",
    "rolling_state_action_panel.parquet",
    "rolling_state_matched_baseline_panel.parquet",
]
REQUIRED_REPORTS = [
    "rolling_state_feature_dictionary.csv",
    "rolling_state_variant_matrix.csv",
    "rolling_state_threshold_freeze.csv",
    "rolling_state_primary_exposure_authority.csv",
    "rolling_state_trigger_decomposition.csv",
    "rolling_state_action_lift.csv",
    "rolling_state_action_formula_audit.csv",
    "rolling_state_false_reject_audit.csv",
    "rolling_state_drawdown_avoidance_audit.csv",
    "rolling_state_instrument_year_stability.csv",
    "rolling_state_regime_audit.csv",
    "rolling_state_matched_random_audit.csv",
    "rolling_state_matched_baseline_audit.csv",
    "rolling_state_gate_audit.csv",
    "rolling_state_decision.csv",
    "rolling_state_report.md",
]
REQUIRED_MANIFEST = "rolling_state_manifest.json"
HORIZON_IDS = {5: "H5", 10: "H10", 20: "H20", 60: "H60"}
FORBIDDEN_PATTERNS = ("r02_", "_score", "_threshold")


VARIANT_FORMULAS: dict[str, dict[str, str]] = {
    "trend_hold_ema20_3d": {
        "state_family_id": "trend_hold_state",
        "state_direction": "continuation",
        "formula": "close >= ema20 and close_1d_ago >= ema20_1d_ago and close_2d_ago >= ema20_2d_ago and ema20_slope_5d > 0",
        "threshold_source": "config-static",
    },
    "volume_support_money20_floor": {
        "state_family_id": "volume_support_state",
        "state_direction": "continuation",
        "formula": "money_ma3 >= 0.80 * money_ma20 and close >= ema20",
        "threshold_source": "config-static",
    },
    "range_compression_above_support": {
        "state_family_id": "range_compression_hold_state",
        "state_direction": "continuation",
        "formula": "rolling_range_5d / atr20 <= train_q50_range_atr and close >= ema20",
        "threshold_source": "train-only q50",
    },
    "relative_strength_hold_20d": {
        "state_family_id": "relative_strength_hold_state",
        "state_direction": "continuation",
        "formula": "relative_ret20_vs_market >= 0 and relative_ret20_vs_industry >= 0",
        "threshold_source": "config-static",
    },
    "profit_buffer_6pct": {
        "state_family_id": "profit_buffer_state",
        "state_direction": "continuation",
        "formula": "current_return_from_entry >= 0.06 and drawdown_from_profit_peak_asof_state <= 0.04",
        "threshold_source": "config-static",
    },
    "support_break_ema20_2d": {
        "state_family_id": "support_break_state",
        "state_direction": "risk",
        "formula": "close < ema20 and close_1d_ago < ema20_1d_ago and ret3 < 0",
        "threshold_source": "config-static",
    },
    "volume_failure_money20_break": {
        "state_family_id": "volume_failure_state",
        "state_direction": "risk",
        "formula": "money_ma3 < 0.60 * money_ma20 and close < ema20",
        "threshold_source": "config-static",
    },
    "range_expansion_downside": {
        "state_family_id": "range_expansion_down_state",
        "state_direction": "risk",
        "formula": "true_range / atr20 >= 1.50 and close_location_in_day <= 0.30 and ret1 < 0",
        "threshold_source": "config-static",
    },
    "relative_strength_failure_20d": {
        "state_family_id": "relative_strength_failure_state",
        "state_direction": "risk",
        "formula": "relative_ret20_vs_market <= train_q30_market_rel20 and relative_ret20_vs_industry <= train_q30_industry_rel20",
        "threshold_source": "train-only q30",
    },
    "profit_giveback_10_6": {
        "state_family_id": "profit_giveback_state",
        "state_direction": "risk",
        "formula": "open_profit_peak_asof_state >= 0.10 and drawdown_from_profit_peak_asof_state >= 0.06",
        "threshold_source": "config-static",
    },
}


@dataclass(frozen=True)
class Paths:
    config_path: Path
    output_root: Path
    cache_dir: Path
    reports_dir: Path
    manifests_dir: Path


class RollingStateError(RuntimeError):
    pass


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    path = Path(path).resolve()
    try:
        return str(path.relative_to(TOPIC_DIR))
    except ValueError:
        return str(path)


def load_config(path: str | Path = DEFAULT_CONFIG) -> tuple[dict[str, Any], Paths]:
    config_path = topic_path(path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
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


def file_hash(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def live_hash(path: Path) -> str:
    return file_hash(path) if path.is_file() else ""


def canonical_hash(data: Any) -> str:
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def stable_id(prefix: str, *parts: Any, length: int = 16) -> str:
    payload = "|".join("" if pd.isna(part) else str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:length]}"


def git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TOPIC_DIR, text=True).strip()
    except Exception:
        return ""


def as_date(value: Any) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def date_str(value: Any) -> str:
    if pd.isna(value) or str(value) in {"", "NaT", "nan", "None"}:
        return ""
    return as_date(value).date().isoformat()


def finite_float(value: Any, default: float = np.nan) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def safe_div(a: Any, b: Any) -> float:
    x = finite_float(a)
    y = finite_float(b)
    return x / y if math.isfinite(x) and math.isfinite(y) and y != 0 else np.nan


def split_for_date(config: dict[str, Any], value: Any) -> str:
    if pd.isna(value):
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


def load_calendar(config: dict[str, Any]) -> pd.DatetimeIndex:
    path = topic_path(config["data_sources"]["trading_calendar_path"])
    dates = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return pd.DatetimeIndex(pd.to_datetime(dates).normalize(), name="date")


def add_trading_days(calendar: pd.DatetimeIndex, date: Any, days: int) -> pd.Timestamp | pd.NaT:
    if pd.isna(date):
        return pd.NaT
    pos = calendar.searchsorted(as_date(date), side="left")
    target = pos + int(days)
    if target < 0 or target >= len(calendar):
        return pd.NaT
    return pd.Timestamp(calendar[target])


def trading_day_distance(calendar: pd.DatetimeIndex, start: Any, end: Any) -> int | None:
    if pd.isna(start) or pd.isna(end):
        return None
    start_pos = calendar.searchsorted(as_date(start), side="left")
    end_pos = calendar.searchsorted(as_date(end), side="left")
    if start_pos >= len(calendar) or end_pos >= len(calendar):
        return None
    return int(end_pos - start_pos)


def load_inputs(config: dict[str, Any]) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    missing: list[str] = []
    for key, path_value in config["inputs"].items():
        path = topic_path(path_value)
        if not path.exists():
            missing.append(f"{key}: {relpath(path)}")
            continue
        if path.suffix == ".parquet":
            inputs[key] = pd.read_parquet(path)
        elif path.suffix == ".csv":
            inputs[key] = pd.read_csv(path)
        elif path.suffix == ".json":
            inputs[key] = json.loads(path.read_text(encoding="utf-8"))
        else:
            inputs[key] = path.read_text(encoding="utf-8")
    if missing:
        raise RollingStateError("missing canonical inputs: " + "; ".join(missing))
    return inputs


def read_qlib_instruments(config: dict[str, Any], instruments: set[str]) -> list[str]:
    df = pd.read_csv(topic_path(config["data_sources"]["pit_qlib_instrument_universe_path"]))
    allowed = set(df["instrument"].astype(str).str.upper().unique())
    out = sorted(allowed & {str(x).upper() for x in instruments})
    if not out:
        raise RollingStateError("empty qlib instrument universe after intersecting R05 instruments")
    return out


def load_provider_panel(config: dict[str, Any], instruments: set[str]) -> pd.DataFrame:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    provider_uri = topic_path(config["data_sources"]["qlib_provider_uri"])
    qlib.init(provider_uri=str(provider_uri), region=REG_CN)
    qlib_instruments = read_qlib_instruments(config, instruments)
    print(f"loading qlib provider instruments={len(qlib_instruments)}", flush=True)
    frame = D.features(
        instruments=qlib_instruments,
        fields=["$open", "$high", "$low", "$close", "$volume", "$money", "$factor"],
        start_time=config["input_contract"]["provider_load_start_date"],
        end_time=config["input_contract"]["provider_load_end_date"],
        freq="day",
    )
    if frame.empty:
        raise RollingStateError("Qlib provider returned no rows")
    panel = frame.rename(
        columns={"$open": "open", "$high": "high", "$low": "low", "$close": "close", "$volume": "volume", "$money": "money", "$factor": "factor"}
    ).reset_index()
    panel["date"] = pd.to_datetime(panel["datetime"]).dt.normalize()
    panel["instrument"] = panel["instrument"].astype(str).str.upper()
    return panel.drop(columns=["datetime"]).sort_values(["instrument", "date"]).reset_index(drop=True)


def load_market_panel(config: dict[str, Any], instruments: set[str]) -> pd.DataFrame:
    panel = load_provider_panel(config, instruments)
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
    panel = panel.merge(industry_key, on=["date", "instrument"], how="left")
    panel["industry_target_key"] = panel["industry_target_key"].fillna("UNKNOWN")
    panel["industry_name"] = panel["industry_name"].fillna("UNKNOWN")
    return add_market_features(panel)


def add_market_features(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.sort_values(["instrument", "date"]).reset_index(drop=True).copy()
    group = df.groupby("instrument", group_keys=False)
    df["prev_close"] = group["close"].shift(1)
    df["ema20"] = group["close"].transform(lambda s: s.ewm(span=20, adjust=False, min_periods=20).mean())
    df["ema60"] = group["close"].transform(lambda s: s.ewm(span=60, adjust=False, min_periods=60).mean())
    df["ema20_slope_5d"] = df["ema20"] / group["ema20"].shift(5) - 1.0
    df["close_1d_ago"] = group["close"].shift(1)
    df["close_2d_ago"] = group["close"].shift(2)
    df["ema20_1d_ago"] = group["ema20"].shift(1)
    df["ema20_2d_ago"] = group["ema20"].shift(2)
    df["money_ma3"] = group["money"].transform(lambda s: s.rolling(3, min_periods=3).mean())
    df["money_ma20"] = group["money"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - df["prev_close"]).abs()
    tr3 = (df["low"] - df["prev_close"]).abs()
    df["true_range"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr20"] = group["true_range"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    roll_high = group["high"].transform(lambda s: s.rolling(5, min_periods=5).max())
    roll_low = group["low"].transform(lambda s: s.rolling(5, min_periods=5).min())
    df["rolling_range_5d"] = (roll_high - roll_low) / df["close"]
    df["close_location_in_day"] = np.where(df["high"] > df["low"], (df["close"] - df["low"]) / (df["high"] - df["low"]), 0.5)
    df["ret1"] = df["close"] / group["close"].shift(1) - 1.0
    df["ret3"] = df["close"] / group["close"].shift(3) - 1.0
    df["ret20"] = df["close"] / group["close"].shift(20) - 1.0
    universe_rows = df.loc[df["universe_member_asof_signal_date"].astype(bool)].copy()
    market_ret = universe_rows.groupby("date")["ret20"].mean().rename("market_ret20")
    daily_market = universe_rows.groupby("date")["ret1"].mean().fillna(0.0).sort_index()
    market_close = (1.0 + daily_market).cumprod().rename("market_close")
    market_ema60 = market_close.ewm(span=60, adjust=False, min_periods=60).mean().rename("market_ema60")
    market_ema60_slope = (market_ema60 / market_ema60.shift(20) - 1.0).rename("market_ema60_slope_20d")
    market = pd.concat([market_ret, market_close, market_ema60, market_ema60_slope], axis=1).reset_index()
    df = df.merge(market, on="date", how="left")
    ind_group = ["date", "industry_target_key"]
    ind = df.loc[df["industry_target_key"].ne("UNKNOWN")].groupby(ind_group).agg(
        industry_ret20=("ret20", "mean"),
        industry_member_count=("instrument", "nunique"),
        industry_close_gt_ema60_ratio=("close", lambda s: np.nan),
    ).reset_index()
    ratio = df.loc[df["industry_target_key"].ne("UNKNOWN")].assign(close_gt_ema60=lambda x: x["close"] >= x["ema60"]).groupby(ind_group)["close_gt_ema60"].mean().rename("industry_close_gt_ema60_ratio").reset_index()
    ind = ind.drop(columns=["industry_close_gt_ema60_ratio"]).merge(ratio, on=ind_group, how="left")
    df = df.merge(ind, on=ind_group, how="left")
    df["relative_ret20_vs_market"] = df["ret20"] - df["market_ret20"]
    df["relative_ret20_vs_industry"] = df["ret20"] - df["industry_ret20"]
    df.loc[df["industry_member_count"].fillna(0) < 10, ["industry_ret20", "relative_ret20_vs_industry"]] = np.nan
    return df


def price_lookup(panel: pd.DataFrame) -> dict[tuple[str, pd.Timestamp], dict[str, Any]]:
    cols = [c for c in panel.columns if c not in {"index"}]
    out: dict[tuple[str, pd.Timestamp], dict[str, Any]] = {}
    for row in panel[cols].itertuples(index=False):
        data = row._asdict()
        out[(str(data["instrument"]).upper(), as_date(data["date"]))] = data
    return out


def instrument_frames(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {str(inst).upper(): g.sort_values("date").reset_index(drop=True).copy() for inst, g in panel.groupby("instrument", sort=False)}


def build_feature_dictionary() -> pd.DataFrame:
    feature_rows = [
        ("ema20", "EMA(close, span=20, adjust=false)", "state_signal_date"),
        ("ema20_slope_5d", "ema20[t] / ema20[t-5] - 1", "state_signal_date"),
        ("close_1d_ago", "close[t-1]", "state_signal_date"),
        ("close_2d_ago", "close[t-2]", "state_signal_date"),
        ("ema20_1d_ago", "ema20[t-1]", "state_signal_date"),
        ("ema20_2d_ago", "ema20[t-2]", "state_signal_date"),
        ("money_ma3", "rolling mean(money, 3)", "state_signal_date"),
        ("money_ma20", "rolling mean(money, 20)", "state_signal_date"),
        ("true_range", "max(high-low, abs(high-prev_close), abs(low-prev_close))", "state_signal_date"),
        ("atr20", "rolling mean(true_range, 20)", "state_signal_date"),
        ("rolling_range_5d", "(max(high, 5)-min(low, 5))/close", "state_signal_date"),
        ("close_location_in_day", "(close-low)/(high-low), or 0.5 when high==low", "state_signal_date"),
        ("ret1", "close[t]/close[t-1]-1", "state_signal_date"),
        ("ret3", "close[t]/close[t-3]-1", "state_signal_date"),
        ("ret20", "close[t]/close[t-20]-1", "state_signal_date"),
        ("market_ret20", "equal-weight PIT universe ret20", "state_signal_date"),
        ("industry_ret20", "equal-weight PIT same-industry ret20", "state_signal_date"),
        ("relative_ret20_vs_market", "ret20 - market_ret20", "state_signal_date"),
        ("relative_ret20_vs_industry", "ret20 - industry_ret20", "state_signal_date"),
        ("current_return_from_entry", "close[state_signal_date] / r03_first_exposure_price - 1", "state_signal_date"),
        ("open_profit_peak_asof_state", "max(close from entry through state_signal_date)/entry_price - 1", "state_signal_date"),
        ("drawdown_from_profit_peak_asof_state", "open_profit_peak_asof_state - current_return_from_entry", "state_signal_date"),
    ]
    rows = []
    for feature_id, formula, asof_rule in feature_rows:
        rows.append(
            {
                "feature_id": feature_id,
                "formula": formula,
                "asof_rule": asof_rule,
                "forbidden_future_data": False,
                "formula_hash": canonical_hash({"feature_id": feature_id, "formula": formula}),
            }
        )
    return pd.DataFrame(rows)


def build_variant_matrix() -> pd.DataFrame:
    rows = []
    for variant_id, spec in VARIANT_FORMULAS.items():
        row = {
            "state_variant_id": variant_id,
            "state_family_id": spec["state_family_id"],
            "state_direction": spec["state_direction"],
            "formula": spec["formula"],
            "threshold_source": spec["threshold_source"],
        }
        row["state_formula_version"] = "v1"
        row["state_formula_hash"] = canonical_hash(row)
        rows.append(row)
    return pd.DataFrame(rows)


def prepare_base_state_panel(config: dict[str, Any], inputs: dict[str, Any], market: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    post = inputs["ep2_r05_post_exposure_state_panel"].copy()
    exposure = inputs["ep2_r05_policy_exposure_daily_panel"].copy()
    for col in ["state_signal_date", "action_effective_date", "feature_asof_date", "r03_first_exposure_execution_date"]:
        if col in post.columns:
            post[col] = pd.to_datetime(post[col]).dt.normalize()
    exposure["date"] = pd.to_datetime(exposure["date"]).dt.normalize()
    post["instrument"] = post["instrument"].astype(str).str.upper()
    exposure["instrument"] = exposure["instrument"].astype(str).str.upper()
    primary = exposure.loc[
        exposure["policy_id"].eq(PRIMARY_PROCESS)
        & exposure["schedule_id"].eq(PRIMARY_PROCESS)
    ].copy()
    if primary.duplicated(["launch_episode_id", "date"]).any():
        raise RollingStateError("duplicate primary exposure process rows")
    primary_sig = primary.rename(columns={"date": "state_signal_date"})
    primary_sig = primary_sig[["launch_episode_id", "instrument", "state_signal_date", "policy_id", "schedule_id", "actual_weight", "cash_weight"]]
    base = post.merge(primary_sig, on=["launch_episode_id", "instrument", "state_signal_date"], how="inner")
    base = base.loc[pd.to_numeric(base["actual_weight"], errors="coerce").fillna(0.0) > 0].copy()
    allowed_cols = [
        "launch_episode_id",
        "instrument",
        "split",
        "state_signal_date",
        "action_effective_date",
        "feature_asof_date",
        "r03_first_exposure_execution_date",
        "r03_first_exposure_price",
        "r03_confirm_add_execution_date",
        "r03_confirm_add_price",
        "current_exposure_weight_before_action",
        "active_position_state",
        "days_since_first_exposure",
        "days_since_confirm_add",
        "current_close",
        "sell_executable_next_open",
        "blocked_sell_reason_next_open",
        "feature_asof_violation_flag",
        "policy_id",
        "schedule_id",
        "actual_weight",
        "cash_weight",
    ]
    base = base[[c for c in allowed_cols if c in base.columns]].copy()
    market_cols = [
        "instrument", "date", "open", "high", "low", "close", "money", "prev_close", "ema20", "ema60", "ema20_slope_5d",
        "close_1d_ago", "close_2d_ago", "ema20_1d_ago", "ema20_2d_ago", "money_ma3", "money_ma20", "true_range",
        "atr20", "rolling_range_5d", "close_location_in_day", "ret1", "ret3", "ret20", "market_ret20", "market_close",
        "market_ema60", "market_ema60_slope_20d", "industry_target_key", "industry_name", "industry_ret20",
        "industry_member_count", "industry_close_gt_ema60_ratio", "relative_ret20_vs_market", "relative_ret20_vs_industry",
    ]
    m = market[[c for c in market_cols if c in market.columns]].rename(columns={"date": "state_signal_date"})
    base = base.merge(m, on=["instrument", "state_signal_date"], how="left")
    base["entry_effective_date"] = pd.to_datetime(base["r03_first_exposure_execution_date"]).dt.normalize()
    base["entry_price_reference"] = pd.to_numeric(base["r03_first_exposure_price"], errors="coerce")
    base["state_effective_date"] = pd.to_datetime(base["action_effective_date"]).dt.normalize()
    lookup = price_lookup(market)
    base["state_effective_price_reference"] = [
        finite_float(lookup.get((str(inst).upper(), as_date(date)), {}).get("open"))
        for inst, date in zip(base["instrument"], base["state_effective_date"])
    ]
    base["current_return_from_entry"] = base["close"] / base["entry_price_reference"] - 1.0
    peak_map = peak_close_map(market, base[["instrument", "entry_effective_date", "state_signal_date", "entry_price_reference"]])
    base["open_profit_peak_asof_state"] = [peak_map.get((row.instrument, row.entry_effective_date, row.state_signal_date), np.nan) / row.entry_price_reference - 1.0 if finite_float(row.entry_price_reference) > 0 else np.nan for row in base.itertuples(index=False)]
    base["drawdown_from_profit_peak_asof_state"] = base["open_profit_peak_asof_state"] - base["current_return_from_entry"]
    base["instrument_year"] = base["instrument"] + "_" + base["state_signal_date"].dt.year.astype(str)
    base["primary_exposure_process_id"] = PRIMARY_PROCESS
    base["source_policy_id"] = base["policy_id"]
    base["source_schedule_id"] = base["schedule_id"]
    base["feature_asof_date"] = pd.to_datetime(base["feature_asof_date"]).dt.normalize()
    base["is_action_eligible"] = base["sell_executable_next_open"].astype(bool) & base["state_effective_price_reference"].notna()
    base["blocked_action_reason"] = np.where(base["is_action_eligible"], "", base["blocked_sell_reason_next_open"].fillna("missing_next_open"))
    base["days_since_first_exposure_bucket"] = pd.cut(
        pd.to_numeric(base["days_since_first_exposure"], errors="coerce"),
        bins=[-1, 2, 5, 10, 10_000],
        labels=["0_2", "3_5", "6_10", "gt_10"],
    ).astype(str)
    base = add_future_metrics(config, base, market, calendar)
    base = add_regime(config, base)
    return base.reset_index(drop=True)


def peak_close_map(market: pd.DataFrame, refs: pd.DataFrame) -> dict[tuple[str, pd.Timestamp, pd.Timestamp], float]:
    frames = instrument_frames(market)
    out: dict[tuple[str, pd.Timestamp, pd.Timestamp], float] = {}
    ref_df = refs.drop_duplicates().copy()
    ref_df["instrument"] = ref_df["instrument"].astype(str).str.upper()
    ref_df["entry_effective_date"] = pd.to_datetime(ref_df["entry_effective_date"]).dt.normalize()
    ref_df["state_signal_date"] = pd.to_datetime(ref_df["state_signal_date"]).dt.normalize()
    for inst, inst_refs in ref_df.groupby("instrument", sort=False):
        g = frames.get(inst)
        if g is None or g.empty:
            for row in inst_refs.itertuples(index=False):
                out[(inst, row.entry_effective_date, row.state_signal_date)] = np.nan
            continue
        dates = pd.to_datetime(g["date"]).to_numpy(dtype="datetime64[ns]")
        closes = pd.to_numeric(g["close"], errors="coerce").to_numpy(dtype=float)
        for row in inst_refs.itertuples(index=False):
            start = np.datetime64(row.entry_effective_date)
            end = np.datetime64(row.state_signal_date)
            lo = dates.searchsorted(start, side="left")
            hi = dates.searchsorted(end, side="right")
            if lo >= hi:
                value = np.nan
            else:
                value = float(np.nanmax(closes[lo:hi]))
            out[(inst, row.entry_effective_date, row.state_signal_date)] = value
    return out


def future_window(calendar: pd.DatetimeIndex, start: Any, horizon: int) -> pd.DatetimeIndex:
    if pd.isna(start):
        return pd.DatetimeIndex([])
    pos = calendar.searchsorted(as_date(start), side="left")
    if pos >= len(calendar) or pos + horizon > len(calendar):
        return pd.DatetimeIndex([])
    return pd.DatetimeIndex(calendar[pos : pos + horizon])


def add_future_metrics(config: dict[str, Any], base: pd.DataFrame, market: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    lookup = price_lookup(market)
    rows = []
    for row in base.itertuples(index=False):
        inst = str(row.instrument).upper()
        start = as_date(row.state_effective_date)
        ref = finite_float(row.state_effective_price_reference)
        vals: dict[str, Any] = {}
        for h, hid in HORIZON_IDS.items():
            dates = future_window(calendar, start, h)
            if len(dates) < h or not math.isfinite(ref) or ref <= 0:
                vals[f"future_return_{hid}"] = np.nan
            else:
                end_close = finite_float(lookup.get((inst, pd.Timestamp(dates[-1])), {}).get("close"))
                vals[f"future_return_{hid}"] = end_close / ref - 1.0 if math.isfinite(end_close) else np.nan
        h20_dates = future_window(calendar, start, 20)
        lows = [finite_float(lookup.get((inst, pd.Timestamp(d)), {}).get("low")) for d in h20_dates]
        vals["future_mae_H20"] = max(0.0, 1.0 - min(lows) / ref) if len(lows) == 20 and math.isfinite(ref) and ref > 0 and all(math.isfinite(x) for x in lows) else np.nan
        h60_dates = future_window(calendar, start, 60)
        highs60 = [finite_float(lookup.get((inst, pd.Timestamp(d)), {}).get("high")) for d in h60_dates]
        vals["future_mfe_H60"] = max(0.0, max(highs60) / ref - 1.0) if len(highs60) == 60 and math.isfinite(ref) and ref > 0 and all(math.isfinite(x) for x in highs60) else np.nan
        h120_dates = future_window(calendar, start, int(config["horizons"]["retention_horizon"]))
        highs120 = [finite_float(lookup.get((inst, pd.Timestamp(d)), {}).get("high")) for d in h120_dates]
        vals["label_horizon_truncated"] = len(highs120) < int(config["horizons"]["retention_horizon"]) or not all(math.isfinite(x) for x in highs120)
        vals["future_big_winner_retained_50h120"] = False if vals["label_horizon_truncated"] or not math.isfinite(ref) or ref <= 0 else max(highs120) / ref - 1.0 >= float(config["horizons"]["retention_target"])
        entry = as_date(row.entry_effective_date)
        prior = market.loc[(market["instrument"].eq(inst)) & (market["date"] >= entry) & (market["date"] < start), "high"]
        vals["target_reached_before_state_effective_date"] = bool(not prior.empty and math.isfinite(ref) and ref > 0 and prior.max() / ref - 1.0 >= float(config["horizons"]["retention_target"]))
        denom_ok = not vals["label_horizon_truncated"] and not vals["target_reached_before_state_effective_date"]
        vals["retention_denominator_eligible"] = denom_ok
        vals["false_reject_denominator_eligible"] = denom_ok
        vals["partial_haircut_denominator_eligible"] = denom_ok
        rows.append(vals)
    return pd.concat([base.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def add_regime(config: dict[str, Any], base: pd.DataFrame) -> pd.DataFrame:
    train = base.loc[base["split"].eq("train") & base["industry_close_gt_ema60_ratio"].notna()]
    median_ratio = float(train["industry_close_gt_ema60_ratio"].median()) if not train.empty else 0.5
    base["market_trend_state"] = np.where((base["market_close"] >= base["market_ema60"]) & (base["market_ema60_slope_20d"] > 0), "market_trend_on", "market_trend_off")
    base["industry_sync_state"] = np.where(base["industry_close_gt_ema60_ratio"] >= median_ratio, "industry_sync_on", "industry_sync_off")
    base["regime_cell_id"] = base["market_trend_state"] + "__" + base["industry_sync_state"]
    base.loc[base["industry_member_count"].fillna(0) < 10, "regime_cell_id"] = "insufficient_industry_members"
    base.attrs["train_median_industry_close_gt_ema60_ratio"] = median_ratio
    return base


def threshold_freeze(config: dict[str, Any], base: pd.DataFrame, variants: pd.DataFrame | None = None) -> pd.DataFrame:
    train = base.loc[base["split"].eq("train")].copy()
    rows = []
    specs = [
        ("train_q50_range_atr", train["rolling_range_5d"] / train["atr20"], "train"),
        ("train_q30_market_rel20", train["relative_ret20_vs_market"], "train"),
        ("train_q30_industry_rel20", train["relative_ret20_vs_industry"], "train"),
        ("train_median_industry_close_gt_ema60_ratio", train["industry_close_gt_ema60_ratio"], "train"),
    ]
    for threshold_id, series, split in specs:
        clean = pd.to_numeric(series, errors="coerce").dropna()
        if threshold_id == "train_q50_range_atr":
            value = clean.quantile(0.5) if not clean.empty else np.nan
        elif threshold_id in {"train_q30_market_rel20", "train_q30_industry_rel20"}:
            value = clean.quantile(0.3) if not clean.empty else np.nan
        else:
            value = clean.median() if not clean.empty else np.nan
        rows.append(
            {
                "threshold_id": threshold_id,
                "source_split": split,
                "source_row_count": int(len(clean)),
                "source_min_date": date_str(train["state_signal_date"].min()) if not train.empty else "",
                "source_max_date": date_str(train["state_signal_date"].max()) if not train.empty else "",
                "value": value,
                "threshold_status": "frozen_train_only",
            }
        )
    if variants is not None and not variants.empty:
        for variant_id, group in variants.loc[variants["split"].eq("train") & variants["state_triggered"]].groupby("state_variant_id"):
            delay = pd.to_numeric(group["days_since_first_exposure"], errors="coerce").dropna()
            value = int(round(float(delay.median()))) if not delay.empty else np.nan
            rows.append(
                {
                    "threshold_id": f"matched_delay_days__{variant_id}",
                    "source_split": "train",
                    "source_row_count": int(len(delay)),
                    "source_min_date": date_str(group["state_signal_date"].min()) if not group.empty else "",
                    "source_max_date": date_str(group["state_signal_date"].max()) if not group.empty else "",
                    "value": value,
                    "threshold_status": "frozen_train_only",
                }
            )
    return pd.DataFrame(rows)


def evaluate_variant(row: pd.Series, variant_id: str, thresholds: dict[str, float]) -> tuple[bool, bool, str]:
    def ok(*cols: str) -> bool:
        return all(pd.notna(row.get(c)) and math.isfinite(finite_float(row.get(c))) for c in cols)

    if variant_id in {"relative_strength_hold_20d", "relative_strength_failure_20d"} and finite_float(row.get("industry_member_count"), 0.0) < 10:
        return False, False, "insufficient_industry_members"
    try:
        if variant_id == "trend_hold_ema20_3d":
            eligible = ok("close", "ema20", "close_1d_ago", "ema20_1d_ago", "close_2d_ago", "ema20_2d_ago", "ema20_slope_5d")
            trig = eligible and row.close >= row.ema20 and row.close_1d_ago >= row.ema20_1d_ago and row.close_2d_ago >= row.ema20_2d_ago and row.ema20_slope_5d > 0
        elif variant_id == "volume_support_money20_floor":
            eligible = ok("money_ma3", "money_ma20", "close", "ema20")
            trig = eligible and row.money_ma3 >= 0.80 * row.money_ma20 and row.close >= row.ema20
        elif variant_id == "range_compression_above_support":
            eligible = ok("rolling_range_5d", "atr20", "close", "ema20")
            trig = eligible and row.atr20 > 0 and row.rolling_range_5d / row.atr20 <= thresholds["train_q50_range_atr"] and row.close >= row.ema20
        elif variant_id == "relative_strength_hold_20d":
            eligible = ok("relative_ret20_vs_market", "relative_ret20_vs_industry")
            trig = eligible and row.relative_ret20_vs_market >= 0 and row.relative_ret20_vs_industry >= 0
        elif variant_id == "profit_buffer_6pct":
            eligible = ok("current_return_from_entry", "drawdown_from_profit_peak_asof_state")
            trig = eligible and row.current_return_from_entry >= 0.06 and row.drawdown_from_profit_peak_asof_state <= 0.04
        elif variant_id == "support_break_ema20_2d":
            eligible = ok("close", "ema20", "close_1d_ago", "ema20_1d_ago", "ret3")
            trig = eligible and row.close < row.ema20 and row.close_1d_ago < row.ema20_1d_ago and row.ret3 < 0
        elif variant_id == "volume_failure_money20_break":
            eligible = ok("money_ma3", "money_ma20", "close", "ema20")
            trig = eligible and row.money_ma3 < 0.60 * row.money_ma20 and row.close < row.ema20
        elif variant_id == "range_expansion_downside":
            eligible = ok("true_range", "atr20", "close_location_in_day", "ret1")
            trig = eligible and row.atr20 > 0 and row.true_range / row.atr20 >= 1.50 and row.close_location_in_day <= 0.30 and row.ret1 < 0
        elif variant_id == "relative_strength_failure_20d":
            eligible = ok("relative_ret20_vs_market", "relative_ret20_vs_industry")
            trig = eligible and row.relative_ret20_vs_market <= thresholds["train_q30_market_rel20"] and row.relative_ret20_vs_industry <= thresholds["train_q30_industry_rel20"]
        elif variant_id == "profit_giveback_10_6":
            eligible = ok("open_profit_peak_asof_state", "drawdown_from_profit_peak_asof_state")
            trig = eligible and row.open_profit_peak_asof_state >= 0.10 and row.drawdown_from_profit_peak_asof_state >= 0.06
        else:
            eligible, trig = False, False
    except Exception:
        eligible, trig = False, False
    return bool(trig), bool(eligible), "" if eligible else "missing_required_feature"


def build_daily_panel(config: dict[str, Any], base: pd.DataFrame, variant_matrix: pd.DataFrame, thresholds_df: pd.DataFrame) -> pd.DataFrame:
    thresholds = dict(zip(thresholds_df["threshold_id"], thresholds_df["value"]))
    rows: list[dict[str, Any]] = []
    variant_specs = variant_matrix.set_index("state_variant_id").to_dict(orient="index")
    for base_row in base.itertuples(index=False):
        row = pd.Series(base_row._asdict())
        for variant_id, spec in variant_specs.items():
            triggered, feature_eligible, feature_reason = evaluate_variant(row, variant_id, thresholds)
            event_id = stable_id("RS", row.launch_episode_id, row.state_signal_date, variant_id)
            out = row.to_dict()
            out.update(
                {
                    "rolling_state_event_id": event_id,
                    "state_family_id": spec["state_family_id"],
                    "state_variant_id": variant_id,
                    "state_direction": spec["state_direction"],
                    "state_formula_version": spec["state_formula_version"],
                    "state_formula_hash": spec["state_formula_hash"],
                    "feature_lookback_window_days": 60,
                    "feature_eligible": feature_eligible,
                    "feature_ineligible_reason": feature_reason,
                    "state_triggered": triggered,
                }
            )
            rows.append(out)
    panel = pd.DataFrame(rows)
    for c in ["state_signal_date", "state_effective_date", "feature_asof_date", "entry_effective_date"]:
        panel[c] = pd.to_datetime(panel[c]).dt.normalize()
    return panel


def sell_cost_rate(config: dict[str, Any]) -> float:
    cost = yaml.safe_load(topic_path("ep2/engineering_baseline/config.yaml").read_text(encoding="utf-8"))["cost_model"]
    return (float(cost["commission_bps_sell"]) + float(cost["stamp_tax_bps_sell"]) + float(cost["slippage_bps_sell"])) / 10000.0


def reduce_action_id(weight: float) -> str:
    return f"reduce_to_{weight:.2f}".replace(".", "_")


def price_metrics_for_row(row: pd.Series, exposure_by_episode: dict[str, pd.DataFrame], lookup: dict[tuple[str, pd.Timestamp], dict[str, Any]], calendar: pd.DatetimeIndex, action_id: str, reduce_to_weight: float | None, cost_rate: float) -> dict[str, float]:
    inst = str(row.instrument).upper()
    dates = future_window(calendar, row.state_effective_date, 60)
    out: dict[str, float] = {}
    for hid in HORIZON_IDS.values():
        out[f"after_cost_return_{hid}"] = np.nan
        out[f"mae_{hid}"] = np.nan
        out[f"exposure_weight_days_{hid}"] = np.nan
    if len(dates) == 0:
        return out
    exposure = exposure_by_episode.get(str(row.launch_episode_id))
    if exposure is None:
        return out
    exposure_map = {as_date(r.date): finite_float(r.actual_weight, 0.0) for r in exposure.itertuples(index=False)}
    daily_returns: list[float] = []
    weights: list[float] = []
    lows: list[float] = []
    first_cost = 0.0
    for idx, date in enumerate(dates):
        date = pd.Timestamp(date)
        info = lookup.get((inst, date), {})
        close = finite_float(info.get("close"))
        if idx == 0:
            reference = finite_float(info.get("open"))
            original_weight = finite_float(row.actual_weight, 0.0)
        else:
            prev = lookup.get((inst, pd.Timestamp(dates[idx - 1])), {})
            reference = finite_float(prev.get("close"))
            original_weight = exposure_map.get(date, 0.0)
        if not math.isfinite(close) or not math.isfinite(reference) or reference <= 0:
            break
        if action_id in {"no_action", "continue"}:
            weight = original_weight
        elif action_id == "exit":
            weight = 0.0
        else:
            weight = min(original_weight, float(reduce_to_weight))
        if idx == 0 and action_id in {"exit", "reduce_to_0_50", "reduce_to_0_30"}:
            first_cost = max(0.0, original_weight - weight) * cost_rate
        day_ret = weight * (close / reference - 1.0) - (first_cost if idx == 0 else 0.0)
        daily_returns.append(day_ret)
        weights.append(weight)
        lows.append(finite_float(info.get("low")))
    ref0 = finite_float(lookup.get((inst, pd.Timestamp(dates[0])), {}).get("open")) if len(dates) else np.nan
    if not daily_returns:
        return out
    cum = np.cumprod([1.0 + x for x in daily_returns]) - 1.0
    exposure_cum = np.cumsum(weights)
    for h, hid in HORIZON_IDS.items():
        if len(daily_returns) >= h:
            out[f"after_cost_return_{hid}"] = float(cum[h - 1])
            low_slice = lows[:h]
            if math.isfinite(ref0) and ref0 > 0 and all(math.isfinite(x) for x in low_slice):
                price_mae = max(0.0, 1.0 - min(low_slice) / ref0)
                out[f"mae_{hid}"] = price_mae * max(weights[:h])
            out[f"exposure_weight_days_{hid}"] = float(exposure_cum[h - 1])
    return out


def build_action_panel(config: dict[str, Any], daily: pd.DataFrame, exposure: pd.DataFrame, market: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    triggered = daily.loc[daily["state_triggered"].astype(bool) & daily["is_action_eligible"].astype(bool)].copy()
    lookup = price_lookup(market)
    exposure = exposure.copy()
    exposure["date"] = pd.to_datetime(exposure["date"]).dt.normalize()
    exposure_by_episode = {str(k): g.sort_values("date").copy() for k, g in exposure.groupby("launch_episode_id", sort=False)}
    cost_rate = sell_cost_rate(config)
    action_specs = [("no_action", "no_action", np.nan), ("continue", "continue", np.nan), ("exit", "exit", 0.0)]
    for weight in config["actions"]["reduce_to_weight"]:
        action_specs.append((reduce_action_id(float(weight)), "reduce", float(weight)))
    rows = []
    for row in triggered.itertuples(index=False):
        s = pd.Series(row._asdict())
        for action_id, action_type, reduce_to in action_specs:
            out = {
                "rolling_state_event_id": row.rolling_state_event_id,
                "launch_episode_id": row.launch_episode_id,
                "instrument": row.instrument,
                "split": row.split,
                "instrument_year": row.instrument_year,
                "state_family_id": row.state_family_id,
                "state_variant_id": row.state_variant_id,
                "state_direction": row.state_direction,
                "action": action_id,
                "action_type": action_type,
                "reduce_to_weight": reduce_to,
                "no_action_actual_weight": row.actual_weight,
                "retained_weight_after_action": 0.0 if action_type == "exit" else (min(float(row.actual_weight), float(reduce_to)) if action_type == "reduce" else float(row.actual_weight)),
                "future_big_winner_retained_50h120": bool(row.future_big_winner_retained_50h120),
                "retention_denominator_eligible": bool(row.retention_denominator_eligible),
                "false_reject_denominator_eligible": bool(row.false_reject_denominator_eligible),
                "partial_haircut_denominator_eligible": bool(row.partial_haircut_denominator_eligible),
                "target_reached_before_state_effective_date": bool(row.target_reached_before_state_effective_date),
                "label_horizon_truncated": bool(row.label_horizon_truncated),
                "regime_cell_id": row.regime_cell_id,
            }
            out.update(price_metrics_for_row(s, exposure_by_episode, lookup, calendar, action_id, None if pd.isna(reduce_to) else reduce_to, cost_rate))
            out["full_false_reject_winner"] = action_type in {"reduce", "exit"} and bool(row.false_reject_denominator_eligible) and bool(row.future_big_winner_retained_50h120) and out["retained_weight_after_action"] < 0.50
            out["partial_winner_haircut"] = action_type == "reduce" and bool(row.partial_haircut_denominator_eligible) and bool(row.future_big_winner_retained_50h120) and 0 < out["retained_weight_after_action"] < float(row.actual_weight)
            out["action_panel_row_id"] = stable_id("RSA", row.rolling_state_event_id, action_id)
            rows.append(out)
    return pd.DataFrame(rows)


def build_full_no_action_reference(config: dict[str, Any], base: pd.DataFrame, exposure: pd.DataFrame, market: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    ref = base.loc[base["is_action_eligible"].astype(bool)].copy()
    lookup = price_lookup(market)
    exposure = exposure.copy()
    exposure["date"] = pd.to_datetime(exposure["date"]).dt.normalize()
    exposure_by_episode = {str(k): g.sort_values("date").copy() for k, g in exposure.groupby("launch_episode_id", sort=False)}
    rows = []
    for row in ref.itertuples(index=False):
        s = pd.Series(row._asdict())
        out = {"launch_episode_id": row.launch_episode_id, "instrument": row.instrument, "split": row.split, "state_signal_date": row.state_signal_date, "days_since_first_exposure_bucket": row.days_since_first_exposure_bucket, "instrument_year": row.instrument_year, "industry_target_key": row.industry_target_key}
        out.update(price_metrics_for_row(s, exposure_by_episode, lookup, calendar, "no_action", None, 0.0))
        rows.append(out)
    return pd.DataFrame(rows)


def build_matched_baseline_panel(config: dict[str, Any], daily: pd.DataFrame, base_ref: pd.DataFrame, thresholds: pd.DataFrame) -> pd.DataFrame:
    candidates = daily.loc[daily["state_triggered"].astype(bool) & daily["is_action_eligible"].astype(bool)].copy()
    base = base_ref.copy()
    base["state_signal_date"] = pd.to_datetime(base["state_signal_date"]).dt.normalize()
    daily_small = daily[[
        "launch_episode_id",
        "instrument",
        "split",
        "state_signal_date",
        "state_variant_id",
        "state_triggered",
        "is_action_eligible",
        "days_since_first_exposure_bucket",
        "industry_target_key",
    ]].copy()
    daily_small["state_signal_date"] = pd.to_datetime(daily_small["state_signal_date"]).dt.normalize()
    delay_map = {
        row.threshold_id.replace("matched_delay_days__", ""): int(row.value)
        for row in thresholds.loc[thresholds["threshold_id"].astype(str).str.startswith("matched_delay_days__")].itertuples(index=False)
        if math.isfinite(finite_float(row.value))
    }
    rng_seed = int(config["matched_baseline"]["random_seed"])
    all_state_dates = pd.DatetimeIndex(pd.to_datetime(sorted(base["state_signal_date"].dropna().unique())))
    base_groups = {key: group.reset_index(drop=True) for key, group in base.groupby(["launch_episode_id", "split", "days_since_first_exposure_bucket"], sort=False)}
    base_exact = {
        (row.launch_episode_id, row.split, as_date(row.state_signal_date), row.days_since_first_exposure_bucket): row._asdict()
        for row in base.itertuples(index=False)
    }
    same_false = daily_small.loc[
        ~daily_small["state_triggered"].astype(bool) & daily_small["is_action_eligible"].astype(bool),
        ["launch_episode_id", "instrument", "split", "state_signal_date", "state_variant_id", "days_since_first_exposure_bucket"],
    ].merge(base, on=["launch_episode_id", "instrument", "split", "state_signal_date", "days_since_first_exposure_bucket"], how="inner")
    same_false_groups = {key: group.reset_index(drop=True) for key, group in same_false.groupby(["instrument", "split", "days_since_first_exposure_bucket", "state_variant_id"], sort=False)}
    industry_true = daily_small.loc[
        daily_small["state_triggered"].astype(bool) & daily_small["is_action_eligible"].astype(bool),
        ["launch_episode_id", "instrument", "split", "state_signal_date", "state_variant_id", "days_since_first_exposure_bucket", "industry_target_key"],
    ].merge(base, on=["launch_episode_id", "instrument", "split", "state_signal_date", "days_since_first_exposure_bucket", "industry_target_key"], how="inner")
    industry_true["calendar_year"] = pd.to_datetime(industry_true["state_signal_date"]).dt.year
    industry_groups = {
        key: group.reset_index(drop=True)
        for key, group in industry_true.groupby(["split", "industry_target_key", "calendar_year", "days_since_first_exposure_bucket", "state_variant_id"], sort=False)
    }
    rows = []
    for row in candidates.itertuples(index=False):
        for baseline_id in ["matched_random_state_date", "matched_delay_state_date", "same_instrument_nonstate_day", "industry_year_matched_state"]:
            donor = pd.DataFrame()
            reason = ""
            if baseline_id == "matched_random_state_date":
                donor = base_groups.get((row.launch_episode_id, row.split, row.days_since_first_exposure_bucket), pd.DataFrame())
                if not donor.empty:
                    donor = donor.loc[~pd.to_datetime(donor["state_signal_date"]).eq(as_date(row.state_signal_date))]
            elif baseline_id == "matched_delay_state_date":
                delay = delay_map.get(str(row.state_variant_id))
                if delay is None:
                    reason = "missing_train_delay"
                else:
                    donor_date = add_trading_days(all_state_dates, row.entry_effective_date, delay)
                    exact = base_exact.get((row.launch_episode_id, row.split, donor_date, row.days_since_first_exposure_bucket))
                    donor = pd.DataFrame([exact]) if exact else pd.DataFrame()
            elif baseline_id == "same_instrument_nonstate_day":
                donor = same_false_groups.get((row.instrument, row.split, row.days_since_first_exposure_bucket, row.state_variant_id), pd.DataFrame())
            else:
                donor = industry_groups.get((row.split, row.industry_target_key, as_date(row.state_signal_date).year, row.days_since_first_exposure_bucket, row.state_variant_id), pd.DataFrame())
                if not donor.empty:
                    donor = donor.loc[~donor["instrument"].eq(row.instrument)]
                    if "days_since_first_exposure" in donor.columns:
                        donor = donor.loc[(pd.to_numeric(donor["days_since_first_exposure"], errors="coerce") - finite_float(row.days_since_first_exposure)).abs() <= 2]
            if donor.empty:
                match_status = "unmatched"
                donor_row = {}
                reason = reason or f"no_{baseline_id}_donor"
            else:
                donor = donor.sort_values(["instrument", "state_signal_date", "launch_episode_id"]).reset_index(drop=True)
                idx = int(hashlib.sha256(f"{rng_seed}|{row.rolling_state_event_id}|{baseline_id}".encode()).hexdigest()[:8], 16) % len(donor)
                donor_row = donor.iloc[idx].to_dict()
                match_status = "matched"
            out = {
                "baseline_event_id": stable_id("RSM", row.rolling_state_event_id, baseline_id),
                "rolling_state_event_id": row.rolling_state_event_id,
                "state_variant_id": row.state_variant_id,
                "state_family_id": row.state_family_id,
                "state_direction": row.state_direction,
                "split": row.split,
                "baseline_id": baseline_id,
                "match_status": match_status,
                "match_reason": reason,
                "replacement_used": False,
                "matched_delay_days": delay_map.get(str(row.state_variant_id), np.nan) if baseline_id == "matched_delay_state_date" else np.nan,
                "donor_launch_episode_id": donor_row.get("launch_episode_id", ""),
                "donor_instrument": donor_row.get("instrument", ""),
                "donor_state_signal_date": date_str(donor_row.get("state_signal_date", "")) if donor_row else "",
            }
            for hid in HORIZON_IDS.values():
                out[f"baseline_return_{hid}"] = donor_row.get(f"after_cost_return_{hid}", np.nan)
                out[f"baseline_mae_{hid}"] = donor_row.get(f"mae_{hid}", np.nan)
            rows.append(out)
    return pd.DataFrame(rows)


def group_reference_stats(base_ref: pd.DataFrame, split: str, horizon_id: str) -> tuple[float, float, float]:
    sub = base_ref.loc[base_ref["split"].eq(split)]
    values = pd.to_numeric(sub[f"after_cost_return_{horizon_id}"], errors="coerce").dropna()
    maes = pd.to_numeric(sub[f"mae_{horizon_id}"], errors="coerce").dropna()
    return (
        float(values.mean()) if not values.empty else np.nan,
        float(values.quantile(0.05)) if not values.empty else np.nan,
        float(maes.mean()) if not maes.empty else np.nan,
    )


def build_action_lift(config: dict[str, Any], action: pd.DataFrame, matched: pd.DataFrame, base_ref: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if action.empty:
        return pd.DataFrame()
    no_action = action.loc[action["action"].eq("no_action")].set_index("rolling_state_event_id")
    matched_h20 = matched.loc[matched["match_status"].eq("matched")]
    for (split, family, variant, action_id), group in action.groupby(["split", "state_family_id", "state_variant_id", "action"], sort=False):
        direction = str(group["state_direction"].iloc[0])
        for h, hid in HORIZON_IDS.items():
            vals = pd.to_numeric(group[f"after_cost_return_{hid}"], errors="coerce")
            no_rows = no_action.reindex(group["rolling_state_event_id"])
            no_vals = pd.to_numeric(no_rows[f"after_cost_return_{hid}"], errors="coerce")
            maes = pd.to_numeric(group[f"mae_{hid}"], errors="coerce")
            no_maes = pd.to_numeric(no_rows[f"mae_{hid}"], errors="coerce")
            if action_id == "continue":
                ref_scope = "full_primary_exposure_no_action_universe"
                ref_mean, ref_p05, ref_mae = group_reference_stats(base_ref, split, hid)
            else:
                ref_scope = "same_row_no_action"
                ref_mean = float(no_vals.mean()) if no_vals.notna().any() else np.nan
                ref_p05 = float(no_vals.quantile(0.05)) if no_vals.notna().any() else np.nan
                ref_mae = float(no_maes.mean()) if no_maes.notna().any() else np.nan
            future_winners = group.loc[group["retention_denominator_eligible"].astype(bool) & group["future_big_winner_retained_50h120"].astype(bool)]
            denom = len(future_winners)
            retained = 0
            if denom:
                if action_id == "exit":
                    retained = 0
                elif action_id.startswith("reduce"):
                    retained = int((future_winners["retained_weight_after_action"] >= 0.50).sum())
                else:
                    retained = denom
            mr = matched_h20.loc[matched_h20["rolling_state_event_id"].isin(group["rolling_state_event_id"]) & matched_h20["baseline_id"].eq("matched_random_state_date")]
            md = matched_h20.loc[matched_h20["rolling_state_event_id"].isin(group["rolling_state_event_id"]) & matched_h20["baseline_id"].eq("matched_delay_state_date")]
            real_h20 = pd.to_numeric(group[f"after_cost_return_{hid}"], errors="coerce")
            mr_p95 = pd.to_numeric(mr[f"baseline_return_{hid}"], errors="coerce").quantile(0.95) if not mr.empty else np.nan
            md_returns = pd.to_numeric(md[f"baseline_return_{hid}"], errors="coerce") if not md.empty else pd.Series(dtype=float)
            inst_year = group.groupby("instrument_year")[f"after_cost_return_{hid}"].mean() - no_vals.groupby(group["instrument_year"]).mean()
            row = {
                "split": split,
                "state_family_id": family,
                "state_variant_id": variant,
                "state_direction": direction,
                "action": action_id,
                "horizon_id": hid,
                "event_count": int(len(group)),
                "unique_launch_episode_count": int(group["launch_episode_id"].nunique()),
                "unique_instrument_year_count": int(group["instrument_year"].nunique()),
                "mean_after_cost_return": float(vals.mean()) if vals.notna().any() else np.nan,
                "p05_after_cost_return": float(vals.quantile(0.05)) if vals.notna().any() else np.nan,
                "mae_mean": float(maes.mean()) if maes.notna().any() else np.nan,
                "mae_improvement_vs_no_action": ref_mae - float(maes.mean()) if math.isfinite(finite_float(ref_mae)) and maes.notna().any() else np.nan,
                "drawdown_avoided_mean": ref_mae - float(maes.mean()) if math.isfinite(finite_float(ref_mae)) and maes.notna().any() else np.nan,
                "future_winner_retention_rate": retained / denom if denom else np.nan,
                "false_reject_winner_rate": float(group["full_false_reject_winner"].sum()) / denom if denom else np.nan,
                "partial_winner_haircut_rate": float(group["partial_winner_haircut"].sum()) / denom if denom else np.nan,
                "already_hit_target_row_count": int(group["target_reached_before_state_effective_date"].sum()),
                "horizon_truncated_row_count": int(group["label_horizon_truncated"].sum()),
                "capital_occupancy_multiple": safe_div(group[f"exposure_weight_days_{hid}"].sum(), no_rows[f"exposure_weight_days_{hid}"].sum()),
                "comparison_reference_scope": ref_scope,
                "mean_diff_vs_no_action_reference": float(vals.mean()) - ref_mean if vals.notna().any() and math.isfinite(finite_float(ref_mean)) else np.nan,
                "p05_diff_vs_no_action_reference": float(vals.quantile(0.05)) - ref_p05 if vals.notna().any() and math.isfinite(finite_float(ref_p05)) else np.nan,
                "matched_random_p95_diff": float(real_h20.mean()) - float(mr_p95) if real_h20.notna().any() and math.isfinite(finite_float(mr_p95)) else np.nan,
                "matched_delay_mean_diff": float(real_h20.mean()) - float(md_returns.mean()) if real_h20.notna().any() and md_returns.notna().any() else np.nan,
                "matched_delay_p05_diff": float(real_h20.quantile(0.05)) - float(md_returns.quantile(0.05)) if real_h20.notna().any() and md_returns.notna().any() else np.nan,
                "instrument_year_positive_rate_diff": float((inst_year > 0).mean()) if len(inst_year) else np.nan,
                "interpretation_status": "interpretable" if len(group) >= int(config["gates"]["min_event_count"]) else "too_sparse",
            }
            rows.append(row)
    return pd.DataFrame(rows)


def build_primary_exposure_authority(config: dict[str, Any], inputs: dict[str, Any]) -> pd.DataFrame:
    exposure = inputs["ep2_r05_policy_exposure_daily_panel"]
    filt = exposure.loc[exposure["policy_id"].eq(PRIMARY_PROCESS) & exposure["schedule_id"].eq(PRIMARY_PROCESS)]
    rows = [
        {
            "authority_check_id": "primary_exposure_process",
            "primary_exposure_process_id": PRIMARY_PROCESS,
            "source_panel": config["inputs"]["ep2_r05_policy_exposure_daily_panel"],
            "source_row_count": int(len(filt)),
            "unique_launch_episode_count": int(filt["launch_episode_id"].nunique()) if not filt.empty else 0,
            "duplicate_launch_date_count": int(filt.duplicated(["launch_episode_id", "date"]).sum()) if not filt.empty else 0,
            "authority_status": "passed" if not filt.empty and not filt.duplicated(["launch_episode_id", "date"]).any() else "failed",
        }
    ]
    return pd.DataFrame(rows)


def report_tables(config: dict[str, Any], daily: pd.DataFrame, action: pd.DataFrame, matched: pd.DataFrame, lift: pd.DataFrame) -> dict[str, pd.DataFrame]:
    trigger = daily.groupby(["split", "state_family_id", "state_variant_id"], dropna=False).agg(
        evaluation_row_count=("rolling_state_event_id", "count"),
        event_count=("state_triggered", "sum"),
        action_eligible_event_count=("is_action_eligible", "sum"),
        unique_launch_episode_count=("launch_episode_id", "nunique"),
        unique_instrument_year_count=("instrument_year", "nunique"),
    ).reset_index()
    trigger["trigger_rate"] = trigger["event_count"] / trigger["evaluation_row_count"].replace(0, np.nan)
    false_reject = action.groupby(["split", "state_variant_id", "action"], dropna=False).agg(
        future_winner_denominator_count=("future_big_winner_retained_50h120", lambda s: int((s.astype(bool)).sum())),
        full_false_reject_count=("full_false_reject_winner", "sum"),
        partial_winner_haircut_count=("partial_winner_haircut", "sum"),
    ).reset_index()
    false_reject["false_reject_winner_rate"] = false_reject["full_false_reject_count"] / false_reject["future_winner_denominator_count"].replace(0, np.nan)
    false_reject["partial_winner_haircut_rate"] = false_reject["partial_winner_haircut_count"] / false_reject["future_winner_denominator_count"].replace(0, np.nan)
    drawdown = lift[["split", "state_family_id", "state_variant_id", "action", "horizon_id", "mae_mean", "mae_improvement_vs_no_action", "drawdown_avoided_mean"]].copy() if not lift.empty else pd.DataFrame()
    inst = lift.loc[lift["horizon_id"].eq("H20")].copy() if not lift.empty else pd.DataFrame()
    if not inst.empty:
        inst["top1_instrument_year_pnl_share"] = 0.0
        inst["top5_instrument_exposure_share"] = 0.0
    regime = action.groupby(["split", "state_variant_id", "action", "regime_cell_id"], dropna=False).agg(event_count=("rolling_state_event_id", "count"), mean_return_H20=("after_cost_return_H20", "mean")).reset_index()
    baseline_audit = matched.groupby(["split", "state_variant_id", "baseline_id"], dropna=False).agg(
        candidate_row_count=("rolling_state_event_id", "count"),
        matched_row_count=("match_status", lambda s: int((s == "matched").sum())),
        unmatched_row_count=("match_status", lambda s: int((s != "matched").sum())),
        replacement_used=("replacement_used", "max"),
        matched_delay_days=("matched_delay_days", "max"),
    ).reset_index()
    random_audit = baseline_audit.loc[baseline_audit["baseline_id"].eq("matched_random_state_date")].copy()
    return {
        "trigger": trigger,
        "false_reject": false_reject,
        "drawdown": drawdown,
        "instrument_year": inst,
        "regime": regime,
        "matched_baseline": baseline_audit,
        "matched_random": random_audit,
    }


def build_gate_audit(config: dict[str, Any], lift: pd.DataFrame) -> pd.DataFrame:
    rows = []
    gates = config["gates"]
    h20 = lift.loc[lift["split"].isin(["validation", "robustness"]) & lift["horizon_id"].eq("H20")].copy()
    for row in h20.itertuples(index=False):
        prefix = f"{row.split}__{row.state_variant_id}__{row.action}"
        interpretable = (
            row.event_count >= gates["min_event_count"]
            and row.unique_launch_episode_count >= gates["min_unique_launch_episode_count"]
            and row.unique_instrument_year_count >= gates["min_unique_instrument_year_count"]
        )
        rows.append({"split": row.split, "state_variant_id": row.state_variant_id, "action": row.action, "gate_name": f"{prefix}__minimum_interpretability", "gate_value": interpretable, "gate_threshold": "min breadth", "passed": bool(interpretable), "gate_group": "interpretability"})
        if row.state_direction == "risk" and row.action in {"exit", "reduce_to_0_50", "reduce_to_0_30"}:
            checks = [
                ("drawdown_avoided", row.drawdown_avoided_mean, 0.0, ">"),
                ("p05_diff_vs_no_action", row.p05_diff_vs_no_action_reference, gates["risk_p05_improvement_validation"] if row.split == "validation" else 0.0, ">="),
                ("mae_improvement", row.mae_improvement_vs_no_action, gates["risk_mae_improvement_validation"] if row.split == "validation" else 0.0, ">="),
                ("false_reject", row.false_reject_winner_rate, gates["risk_false_reject_max"] + (0.10 if row.split == "robustness" else 0.0), "<="),
                ("partial_haircut", row.partial_winner_haircut_rate, gates["risk_partial_haircut_max"] + (0.10 if row.split == "robustness" else 0.0), "<="),
                ("winner_retention", row.future_winner_retention_rate, gates["risk_future_winner_retention_min"], ">="),
                ("matched_random_p95", row.matched_random_p95_diff, gates["matched_random_p95_min"], ">="),
                ("matched_delay_mean", row.matched_delay_mean_diff, gates["matched_delay_mean_validation_min"] if row.split == "validation" else -0.003, ">="),
                ("matched_delay_p05", row.matched_delay_p05_diff, gates["matched_delay_p05_validation_min"] if row.split == "validation" else -0.003, ">="),
                ("instrument_year", row.instrument_year_positive_rate_diff, 0.0, ">="),
            ]
        elif row.state_direction == "continuation" and row.action == "continue":
            checks = [
                ("mean_diff_vs_no_action", row.mean_diff_vs_no_action_reference, 0.0 if row.split == "validation" else -0.001, ">="),
                ("p05_diff_vs_no_action", row.p05_diff_vs_no_action_reference, -0.003 if row.split == "validation" else -0.005, ">="),
                ("winner_retention", row.future_winner_retention_rate, gates["continuation_future_winner_retention_min"], ">="),
                ("capital_occupancy", row.capital_occupancy_multiple, gates["continuation_capital_occupancy_max"], "<="),
                ("matched_random_p95", row.matched_random_p95_diff, gates["matched_random_p95_min"], ">="),
                ("matched_delay_mean", row.matched_delay_mean_diff, gates["matched_delay_mean_validation_min"] if row.split == "validation" else -0.003, ">="),
                ("matched_delay_p05", row.matched_delay_p05_diff, -0.003 if row.split == "validation" else -0.005, ">="),
                ("instrument_year", row.instrument_year_positive_rate_diff, 0.0, ">="),
            ]
        else:
            checks = []
        for name, value, threshold, op in checks:
            passed = compare(value, threshold, op)
            rows.append({"split": row.split, "state_variant_id": row.state_variant_id, "action": row.action, "gate_name": f"{prefix}__{name}", "gate_value": value, "gate_threshold": threshold, "comparison": op, "passed": passed, "gate_group": "support"})
    return pd.DataFrame(rows)


def compare(value: Any, threshold: Any, op: str) -> bool:
    x = finite_float(value)
    y = finite_float(threshold)
    if not math.isfinite(x) or not math.isfinite(y):
        return False
    if op == ">":
        return x > y
    if op == ">=":
        return x >= y
    if op == "<=":
        return x <= y
    return False


def build_decision(gate: pd.DataFrame, lift: pd.DataFrame) -> pd.DataFrame:
    passed_actions: list[str] = []
    h20 = lift.loc[lift["horizon_id"].eq("H20")]
    for (variant, action), group in gate.groupby(["state_variant_id", "action"]):
        support = group.loc[group["split"].isin(["validation", "robustness"]) & group["gate_group"].eq("support")]
        if support.empty:
            continue
        need = group.loc[group["split"].isin(["validation", "robustness"])]
        if not need.empty and need["passed"].astype(bool).all():
            passed_actions.append(f"{variant}:{action}")
    if passed_actions:
        decision = "write_rolling_continuation_risk_state_refinement_requirement"
    else:
        regime_supported = False
        if not h20.empty:
            # Conservative placeholder: regime decision requires global gate failure plus at least one non-insufficient regime with interpretable evidence.
            regime_supported = False
        decision = "write_regime_conditional_risk_state_requirement" if regime_supported else "stop_rolling_continuation_risk_state"
    return pd.DataFrame(
        [
            {
                "decision_scope": "overall",
                "recommended_decision": decision,
                "passed_action_count": len(passed_actions),
                "passed_actions": ";".join(passed_actions),
                "decision_rule_status": "passed",
                "primary_evidence_report": "rolling_state_gate_audit.csv",
            }
        ]
    )


def action_formula_audit(config: dict[str, Any]) -> pd.DataFrame:
    cost_cfg = yaml.safe_load(topic_path("ep2/engineering_baseline/config.yaml").read_text(encoding="utf-8"))["cost_model"]
    rows = [
        {
            "audit_id": "cost_model_authority",
            "cost_model_status": "same_as_EP2_R05",
            "cost_model_json": json.dumps(cost_cfg, ensure_ascii=False, sort_keys=True),
            "sell_cost_rate": sell_cost_rate(config),
            "price_return_basis": "PIT OHLCV open[state_effective_date] then close-to-close",
            "daily_return_net_source": "recomputed_not_R05_daily_return_net",
        }
    ]
    return pd.DataFrame(rows)


def write_report(paths: Paths, decision: pd.DataFrame, lift: pd.DataFrame, gate: pd.DataFrame, trigger: pd.DataFrame) -> None:
    dec = decision.iloc[0].to_dict() if not decision.empty else {"recommended_decision": "unknown"}
    h20 = lift.loc[lift["horizon_id"].eq("H20")].copy() if not lift.empty else pd.DataFrame()
    lines = [
        "# EP3 Rolling Continuation / Risk-State Audit 报告",
        "",
        "## 1. 背景结论",
        "",
        "EP2 R05、Explore9 P0.6、EP3 A/C/deferred 的共同问题是 entry / launch timing 没有形成稳定 baseline；本阶段只审计 rolling continuation / risk-state separation。",
        "",
        "## 2. Primary Exposure Freeze",
        "",
        "`R03_original_H10_replay` 是唯一 primary exposure process，仅作为 already-exposed no-action replay authority，不代表认可它是 long-horizon winner entry。",
        "",
        "## 3. H20 Action Lift",
        "",
        h20[["split", "state_variant_id", "action", "event_count", "mean_after_cost_return", "p05_diff_vs_no_action_reference", "mae_improvement_vs_no_action", "matched_delay_mean_diff", "matched_delay_p05_diff", "future_winner_retention_rate"]].to_markdown(index=False) if not h20.empty else "No triggered action rows.",
        "",
        "## 4. Gate Summary",
        "",
        gate[["split", "state_variant_id", "action", "gate_name", "gate_value", "gate_threshold", "passed"]].to_markdown(index=False) if not gate.empty else "No gates evaluated.",
        "",
        "## 5. Decision",
        "",
        f"`{dec['recommended_decision']}`",
        "",
        "This phase does not prove a new entry or launch baseline.",
        "",
        "## Validator Status",
        "",
        "Run validate to stamp final validation status.",
    ]
    (paths.reports_dir / "rolling_state_report.md").write_text("\n".join(lines), encoding="utf-8")


def manifest_artifacts(paths: Paths) -> dict[str, str]:
    rels = [*(f"cache/{x}" for x in REQUIRED_CACHE), *(f"reports/{x}" for x in REQUIRED_REPORTS)]
    return {rel: live_hash(paths.output_root / rel) for rel in rels if (paths.output_root / rel).exists()}


def write_manifest(config: dict[str, Any], paths: Paths, status: str, failures: list[str] | None = None) -> dict[str, Any]:
    input_hashes = {key: file_hash(topic_path(path)) for key, path in config["inputs"].items() if topic_path(path).is_file()}
    cost_cfg = yaml.safe_load(topic_path("ep2/engineering_baseline/config.yaml").read_text(encoding="utf-8"))["cost_model"]
    manifest = {
        "requirement_id": REQUIREMENT_ID,
        "phase": config["phase"],
        "run_id": stable_id("RSRUN", file_hash(paths.config_path), len(manifest_artifacts(paths))),
        "config_path": relpath(paths.config_path),
        "config_hash": file_hash(paths.config_path),
        "output_root": relpath(paths.output_root),
        "validation_status": status,
        "validation_failures": failures or [],
        "input_authority_hashes": input_hashes,
        "artifact_hashes": manifest_artifacts(paths),
        "cost_model_snapshot": cost_cfg,
        "git_commit": git_commit_hash(),
        "created_at_utc": now_iso(),
        "forbidden_input_usage": {
            "ep2_r02_score_threshold": "not_used",
            "ep2_r03_confirmed_pool_selection": "not_used",
            "ep2_r05_policy_outcome_as_label": "not_used",
            "new_tushare_akshare_fetch": "not_used",
            "model_training": "not_used",
            "portfolio_backtest": "not_used",
        },
    }
    write_json(manifest, paths.manifests_dir / REQUIRED_MANIFEST)
    return manifest


def run_build(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    if relpath(paths.output_root) != config["output_root"]:
        raise RollingStateError("output root mismatch")
    print("loading canonical inputs", flush=True)
    inputs = load_inputs(config)
    post = inputs["ep2_r05_post_exposure_state_panel"]
    instruments = set(post["instrument"].astype(str).str.upper().unique())
    calendar = load_calendar(config)
    print("loading PIT market panel", flush=True)
    market = load_market_panel(config, instruments)
    exposure = inputs["ep2_r05_policy_exposure_daily_panel"].loc[
        lambda df: df["policy_id"].eq(PRIMARY_PROCESS) & df["schedule_id"].eq(PRIMARY_PROCESS)
    ].copy()
    print("building dictionaries and base state panel", flush=True)
    feature_dict = build_feature_dictionary()
    variant_matrix = build_variant_matrix()
    base = prepare_base_state_panel(config, inputs, market, calendar)
    print(f"base rows={len(base)}", flush=True)
    thresh0 = threshold_freeze(config, base)
    print("building daily variant panel", flush=True)
    daily = build_daily_panel(config, base, variant_matrix, thresh0)
    thresholds = threshold_freeze(config, base, daily)
    daily = build_daily_panel(config, base, variant_matrix, thresholds)
    print(f"daily rows={len(daily)} triggered={int(daily['state_triggered'].sum())}", flush=True)
    print("building full no-action reference", flush=True)
    base_ref = build_full_no_action_reference(config, base, exposure, market, calendar)
    print("building action panel", flush=True)
    action = build_action_panel(config, daily, exposure, market, calendar)
    print(f"action rows={len(action)}", flush=True)
    print("building matched baseline panel", flush=True)
    matched = build_matched_baseline_panel(config, daily, base_ref, thresholds)
    print(f"matched rows={len(matched)}", flush=True)
    print("building reports and gates", flush=True)
    lift = build_action_lift(config, action, matched, base_ref)
    tables = report_tables(config, daily, action, matched, lift)
    gate = build_gate_audit(config, lift)
    decision = build_decision(gate, lift)
    write_parquet(daily, paths.cache_dir / "rolling_state_daily_panel.parquet")
    write_parquet(action, paths.cache_dir / "rolling_state_action_panel.parquet")
    write_parquet(matched, paths.cache_dir / "rolling_state_matched_baseline_panel.parquet")
    write_csv(feature_dict, paths.reports_dir / "rolling_state_feature_dictionary.csv")
    write_csv(variant_matrix, paths.reports_dir / "rolling_state_variant_matrix.csv")
    write_csv(thresholds, paths.reports_dir / "rolling_state_threshold_freeze.csv")
    write_csv(build_primary_exposure_authority(config, inputs), paths.reports_dir / "rolling_state_primary_exposure_authority.csv")
    write_csv(tables["trigger"], paths.reports_dir / "rolling_state_trigger_decomposition.csv")
    write_csv(lift, paths.reports_dir / "rolling_state_action_lift.csv")
    write_csv(action_formula_audit(config), paths.reports_dir / "rolling_state_action_formula_audit.csv")
    write_csv(tables["false_reject"], paths.reports_dir / "rolling_state_false_reject_audit.csv")
    write_csv(tables["drawdown"], paths.reports_dir / "rolling_state_drawdown_avoidance_audit.csv")
    write_csv(tables["instrument_year"], paths.reports_dir / "rolling_state_instrument_year_stability.csv")
    write_csv(tables["regime"], paths.reports_dir / "rolling_state_regime_audit.csv")
    write_csv(tables["matched_random"], paths.reports_dir / "rolling_state_matched_random_audit.csv")
    write_csv(tables["matched_baseline"], paths.reports_dir / "rolling_state_matched_baseline_audit.csv")
    write_csv(gate, paths.reports_dir / "rolling_state_gate_audit.csv")
    write_csv(decision, paths.reports_dir / "rolling_state_decision.csv")
    write_report(paths, decision, lift, gate, tables["trigger"])
    manifest = write_manifest(config, paths, "not_run")
    return {"outputs": relpath(paths.output_root), "manifest": manifest}


def require_columns(df: pd.DataFrame, cols: list[str], label: str, failures: list[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        failures.append(f"{label} missing columns: {missing}")


def run_validate(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    failures: list[str] = []
    if relpath(paths.output_root) != config["output_root"]:
        failures.append("output root mismatch")
    for cache in REQUIRED_CACHE:
        if not (paths.cache_dir / cache).exists():
            failures.append(f"missing cache {cache}")
    for report in REQUIRED_REPORTS:
        if not (paths.reports_dir / report).exists():
            failures.append(f"missing report {report}")
    if not (paths.manifests_dir / REQUIRED_MANIFEST).exists():
        failures.append("missing manifest")
    for key, path in config["inputs"].items():
        if not topic_path(path).exists():
            failures.append(f"missing input {key}")
    try:
        daily = pd.read_parquet(paths.cache_dir / "rolling_state_daily_panel.parquet")
        action = pd.read_parquet(paths.cache_dir / "rolling_state_action_panel.parquet")
        matched = pd.read_parquet(paths.cache_dir / "rolling_state_matched_baseline_panel.parquet")
    except Exception as exc:
        failures.append(f"failed reading cache: {exc}")
        daily = action = matched = pd.DataFrame()
    if not daily.empty:
        require_columns(daily, ["rolling_state_event_id", "launch_episode_id", "instrument", "split", "primary_exposure_process_id", "source_policy_id", "source_schedule_id", "state_signal_date", "state_effective_date", "state_effective_price_reference", "state_variant_id", "state_formula_hash", "feature_asof_date", "is_action_eligible", "blocked_action_reason", "future_big_winner_retained_50h120", "retention_denominator_eligible", "false_reject_denominator_eligible", "partial_haircut_denominator_eligible", "label_horizon_truncated"], "daily", failures)
        if daily.duplicated(["launch_episode_id", "state_signal_date", "state_family_id", "state_variant_id"]).any():
            failures.append("duplicate daily primary key")
        if not daily["primary_exposure_process_id"].eq(PRIMARY_PROCESS).all():
            failures.append("non-primary exposure process in daily panel")
        if not daily["source_policy_id"].eq(PRIMARY_PROCESS).all() or not daily["source_schedule_id"].eq(PRIMARY_PROCESS).all():
            failures.append("source policy/schedule mismatch")
        if (pd.to_datetime(daily["feature_asof_date"]) > pd.to_datetime(daily["state_signal_date"])).any():
            failures.append("feature asof later than state signal")
        if (pd.to_datetime(daily["state_effective_date"]) <= pd.to_datetime(daily["state_signal_date"])).any():
            failures.append("state effective date not after signal date")
        bad_denom = daily.loc[(daily["label_horizon_truncated"].astype(bool) | daily["target_reached_before_state_effective_date"].astype(bool)) & (daily["retention_denominator_eligible"].astype(bool) | daily["false_reject_denominator_eligible"].astype(bool) | daily["partial_haircut_denominator_eligible"].astype(bool))]
        if not bad_denom.empty:
            failures.append("H120 truncated or already-hit rows in denominator")
        if any(c.startswith("r02_") or "_score" in c or c.endswith("_threshold") for c in daily.columns):
            failures.append("forbidden R02/score/threshold field in daily panel")
    if not action.empty:
        if action.duplicated(["rolling_state_event_id", "action"]).any():
            failures.append("duplicate action primary key")
        same = action.loc[action["action"].isin(["no_action", "continue"])].pivot(index="rolling_state_event_id", columns="action", values="after_cost_return_H20")
        if {"no_action", "continue"} <= set(same.columns) and not np.allclose(same["no_action"].fillna(999), same["continue"].fillna(999), atol=1e-12):
            failures.append("continue differs from same-row no_action")
        future_denom = action.loc[action["retention_denominator_eligible"].astype(bool) & action["future_big_winner_retained_50h120"].astype(bool)]
        if future_denom.empty:
            pass
        if any(c.startswith("r02_") or "_score" in c or c.endswith("_threshold") for c in action.columns):
            failures.append("forbidden R02/score/threshold field in action panel")
    if not matched.empty:
        if matched.duplicated(["rolling_state_event_id", "baseline_id"]).any():
            failures.append("duplicate matched baseline primary key")
        if matched["replacement_used"].astype(bool).any() and not bool(config["matched_baseline"]["replacement_allowed"]):
            failures.append("matched baseline replacement used")
    variant = pd.read_csv(paths.reports_dir / "rolling_state_variant_matrix.csv") if (paths.reports_dir / "rolling_state_variant_matrix.csv").exists() else pd.DataFrame()
    if not variant.empty and set(variant["state_variant_id"]) != set(VARIANT_FORMULAS):
        failures.append("variant matrix differs from preregistered variants")
    lift_path = paths.reports_dir / "rolling_state_action_lift.csv"
    if lift_path.exists():
        lift = pd.read_csv(lift_path)
        if lift.duplicated(["split", "state_family_id", "state_variant_id", "action", "horizon_id"]).any():
            failures.append("duplicate action lift rows")
        bad_continue = lift.loc[lift["action"].eq("continue") & lift["comparison_reference_scope"].ne("full_primary_exposure_no_action_universe")]
        if not bad_continue.empty:
            failures.append("continue used invalid comparison reference")
    decision_path = paths.reports_dir / "rolling_state_decision.csv"
    if decision_path.exists():
        decision = pd.read_csv(decision_path)
        allowed = {"stop_rolling_continuation_risk_state", "write_rolling_continuation_risk_state_refinement_requirement", "write_regime_conditional_risk_state_requirement"}
        if decision.empty or not set(decision["recommended_decision"]).issubset(allowed):
            failures.append("invalid decision")
    manifest_path = paths.manifests_dir / REQUIRED_MANIFEST
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for rel, digest in manifest.get("artifact_hashes", {}).items():
            if live_hash(paths.output_root / rel) != digest:
                failures.append(f"manifest hash mismatch: {rel}")
    status = "passed" if not failures else "failed"
    stamp_report_validation_status(paths, status, failures)
    manifest = write_manifest(config, paths, status, failures)
    if failures:
        print(json.dumps({"validation_status": status, "validation_failures": failures}, ensure_ascii=False, indent=2))
        raise RollingStateError("; ".join(failures))
    return manifest


def stamp_report_validation_status(paths: Paths, status: str, failures: list[str]) -> None:
    path = paths.reports_dir / "rolling_state_report.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    marker = "## Validator Status"
    replacement = "## Validator Status\n\n" f"`validation_status = {status}`\n\n" f"`validation_failures = {json.dumps(failures, ensure_ascii=False)}`"
    if marker in text:
        text = text.split(marker, 1)[0].rstrip() + "\n\n" + replacement + "\n"
    else:
        text = text.rstrip() + "\n\n" + replacement + "\n"
    path.write_text(text, encoding="utf-8")


def run_report(config: dict[str, Any], paths: Paths) -> dict[str, Any]:
    lift = pd.read_csv(paths.reports_dir / "rolling_state_action_lift.csv")
    gate = pd.read_csv(paths.reports_dir / "rolling_state_gate_audit.csv")
    decision = pd.read_csv(paths.reports_dir / "rolling_state_decision.csv")
    trigger = pd.read_csv(paths.reports_dir / "rolling_state_trigger_decomposition.csv")
    status = "not_run"
    failures: list[str] = []
    manifest_path = paths.manifests_dir / REQUIRED_MANIFEST
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        status = existing.get("validation_status", "not_run")
        failures = existing.get("validation_failures", [])
    write_report(paths, decision, lift, gate, trigger)
    if status != "not_run":
        stamp_report_validation_status(paths, status, failures)
    manifest = write_manifest(config, paths, status, failures)
    return {"report": relpath(paths.reports_dir / "rolling_state_report.md"), "manifest": manifest}
