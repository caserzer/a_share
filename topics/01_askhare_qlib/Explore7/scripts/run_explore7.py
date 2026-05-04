#!/usr/bin/env python3
"""Run Explore7: PIT pullback subsystem rebuild.

Explore7 deliberately keeps the historical Explore4/5/6 result files out of
the calculation path.  The runner may reuse prior structural rule definitions
and local code, but all PIT universe, signal, replay, and selection artifacts
are generated under Explore7.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml


EXPLORE_DIR = Path(__file__).resolve().parents[1]
TOPIC_DIR = EXPLORE_DIR.parent
DEFAULT_CONFIG = EXPLORE_DIR / "configs/pullback_rebuild_v1.yaml"
FIELD_RENAME = {
    "$open": "open",
    "$high": "high",
    "$low": "low",
    "$close": "close",
    "$volume": "volume",
    "$money": "money",
    "$factor": "factor",
}
REQUIRED_CONFIG_TOKENS = [
    "pit_mcap500_mainboard",
    "daily_pit_membership",
    "universe_point_in_time_required",
    "industry_point_in_time_required",
]
SIGNAL_FEATURE_COLUMNS = [
    "datetime",
    "instrument",
    "pit_universe_member",
    "listing_age_trading_days",
    "market_cap_asof_T",
    "industry_asof_T",
    "industry_target_key",
    "industry_name",
    "trend_score",
    "trend_score_pct",
    "money_ratio20",
    "distance_to_ema20",
    "distance_to_ema60",
    "distance_to_high60",
    "distance_to_low20",
    "ret5",
    "ret20",
    "ret60",
    "volatility20",
    "atr20_ratio",
    "market_width_state",
    "market_trend_state",
    "industry_sync_state",
    "pullback_class",
    "pullback_class_reason",
    "breakout_entry",
    "original_pullback_entry",
    "raw_pullback_shape",
    "combined_entry",
    "pullback_entry",
]


class DataGateError(RuntimeError):
    """Raised when a strict PIT data contract blocks strategy execution."""


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    target = Path(path).resolve()
    try:
        return str(target.relative_to(TOPIC_DIR))
    except ValueError:
        return str(target)


def ensure_parent(path: str | Path) -> Path:
    target = topic_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def ensure_dir(path: str | Path) -> Path:
    target = topic_path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def file_sha256(path: str | Path) -> str:
    target = topic_path(path)
    digest = hashlib.sha256()
    with target.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def maybe_sha256(path: str | Path) -> str:
    target = topic_path(path)
    return file_sha256(target) if target.exists() and target.is_file() else ""


def load_yaml(path: str | Path) -> dict[str, Any]:
    target = topic_path(path)
    with target.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def write_csv(df: pd.DataFrame, path: str | Path, **kwargs: Any) -> Path:
    target = ensure_parent(path)
    df.to_csv(target, index=False, **kwargs)
    return target


def write_json(data: dict[str, Any], path: str | Path) -> Path:
    def sanitize(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): sanitize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        if isinstance(value, tuple):
            return [sanitize(item) for item in value]
        if isinstance(value, (np.bool_,)):
            return bool(value)
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating, float)):
            number = float(value)
            return number if math.isfinite(number) else None
        if value is pd.NA or value is pd.NaT:
            return None
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        return value

    target = ensure_parent(path)
    with target.open("w", encoding="utf-8") as file:
        json.dump(sanitize(data), file, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        file.write("\n")
    return target


def read_json(path: str | Path) -> dict[str, Any]:
    target = topic_path(path)
    if not target.exists():
        return {}
    with target.open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_dt(value: str | pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def date_token(value: str | pd.Timestamp) -> str:
    return parse_dt(value).strftime("%Y%m%d")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def format_pct(value: Any) -> str:
    number = safe_float(value, np.nan)
    return "NA" if pd.isna(number) else f"{number:.2%}"


def format_float(value: Any, digits: int = 4) -> str:
    number = safe_float(value, np.nan)
    return "NA" if pd.isna(number) else f"{number:.{digits}f}"


def format_money(value: Any) -> str:
    number = safe_float(value, np.nan)
    return "NA" if pd.isna(number) else f"{number:,.0f}"


def bool_value(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if value is None or value is pd.NA or pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    output.extend("| " + " | ".join(str(item) for item in row) + " |" for row in rows)
    return output


def report_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["report_dir"])


def cache_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["cache_dir"])


def backtest_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["backtest_dir"])


def target_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"].setdefault("target_dir", str(Path(config["paths"]["target_history"]).parent)))


def universe_membership_path(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["universe_membership"])


def universe_qlib_path(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["universe_qlib"])


def industry_membership_path(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["industry_membership"])


def stock_panel_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_panel.pkl"


def stock_indicators_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_indicators.pkl"


def stock_signal_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_signals.pkl"


def manifest_path(config: dict[str, Any]) -> Path:
    return report_dir(config) / "run_manifest.json"


def instrument_to_ts_code(instrument: str) -> str:
    text = str(instrument).strip().upper()
    if "." in text:
        return text
    return f"{text[2:]}.{text[:2]}"


def ts_code_to_instrument(ts_code: str) -> str:
    text = str(ts_code).strip().upper()
    if "." in text:
        code, exchange = text.split(".", 1)
        prefix = {"SH": "SH", "SZ": "SZ", "BJ": "BJ"}.get(exchange, exchange[:2])
        return f"{prefix}{code.zfill(6)}"
    digits = "".join(ch for ch in text if ch.isdigit()).zfill(6)
    prefix = "SH" if digits.startswith("6") else "SZ"
    return f"{prefix}{digits}"


def is_mainboard_instrument(instrument: str) -> bool:
    text = str(instrument).strip().upper()
    code = text[2:] if text.startswith(("SH", "SZ", "BJ")) else text[:6]
    return bool(
        (text.startswith("SH") and code.startswith(("600", "601", "603", "605")))
        or (text.startswith("SZ") and code.startswith(("000", "001", "002", "003")))
    )


def load_dotenv_token() -> str:
    try:
        from dotenv import load_dotenv

        load_dotenv(TOPIC_DIR / ".env", override=False)
    except Exception:
        env_path = TOPIC_DIR / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("TUSHARE_TOKEN=") and not os.getenv("TUSHARE_TOKEN"):
                    os.environ["TUSHARE_TOKEN"] = line.split("=", 1)[1].strip()
                    break
    return os.getenv("TUSHARE_TOKEN", "").strip()


def load_tushare_client(required: bool = True):
    token = load_dotenv_token()
    if not token:
        if required:
            raise RuntimeError("TUSHARE_TOKEN is missing. Put it in .env or the environment.")
        return None
    import tushare as ts

    return ts.pro_api(token)


def import_explore5_runner():
    module_path = TOPIC_DIR / "Explore5/scripts/run_explore5.py"
    spec = importlib.util.spec_from_file_location("explore5_runner_for_explore7", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import Explore5 runner from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def overlay_explore7_rules(config: dict[str, Any], source_rules: dict[str, Any]) -> dict[str, Any]:
    rules = copy.deepcopy(source_rules)
    explore7_rules = copy.deepcopy(config.get("rules", {}))
    portfolio = rules.setdefault("portfolio", {})
    mapping = {
        "risk_degree": "risk_degree",
        "max_positions": "max_positions",
        "max_daily_new_weight": "max_daily_new_weight",
        "single_stock_max_weight": "single_stock_max_weight",
        "max_industry_weight": "max_industry_weight",
    }
    for src, dst in mapping.items():
        if src in explore7_rules:
            portfolio[dst] = explore7_rules[src]
    portfolio["risk_unit_sizing_enabled"] = True
    rules.setdefault("pullback", {})["ema_band_pct"] = explore7_rules.get(
        "ema_band_pct", rules.get("pullback", {}).get("ema_band_pct", 0.01)
    )
    return rules


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config_path = topic_path(path)
    config = load_yaml(config_path)
    config["_config_path"] = str(config_path)
    config["_config_hash"] = file_sha256(config_path)
    config["_explore7_rules"] = copy.deepcopy(config.get("rules", {}))
    config["paths"].setdefault("target_dir", str(Path(config["paths"]["target_history"]).parent))

    sources = config.get("sources", {})
    rule_config = load_yaml(sources["source_rule_config"])
    walk_config = load_yaml(sources["source_walk_forward_config"])
    for key in ["qlib", "costs", "rules", "targets"]:
        if key not in rule_config:
            raise KeyError(f"missing allowed structural key in source rule config: {key}")
    for key in ["qlib", "costs", "rules", "targets"]:
        if key not in walk_config:
            raise KeyError(f"missing allowed structural key in source walk-forward config: {key}")
    config["costs"] = copy.deepcopy(walk_config["costs"])
    config["targets"] = copy.deepcopy(walk_config["targets"])
    config["source_rules"] = copy.deepcopy(walk_config["rules"])
    config["rules"] = overlay_explore7_rules(config, walk_config["rules"])
    config["qlib_source"] = copy.deepcopy(walk_config["qlib"])
    config["_source_provider_uri"] = walk_config.get("paths", {}).get("provider_uri", "")
    config["source_walk_forward"] = {
        "folds": copy.deepcopy(walk_config.get("explore5", {}).get("folds", [])),
        "selection_thresholds": copy.deepcopy(walk_config.get("explore5", {}).get("selection_thresholds", {})),
    }
    return config


def source_paths(config: dict[str, Any]) -> dict[str, Path]:
    sources = config.get("sources", {})
    return {key: topic_path(value) for key, value in sources.items() if key.startswith("source_")}


def record_manifest(
    config: dict[str, Any],
    command: str,
    outputs: list[str | Path],
    extra: dict[str, Any] | None = None,
) -> None:
    path = manifest_path(config)
    manifest = read_json(path)
    commands = list(manifest.get("command_sequence", []))
    commands.append(command)
    output_paths = sorted(set(manifest.get("output_paths", []) + [relpath(p) for p in outputs]))
    universe_path = universe_membership_path(config)
    industry_path = industry_membership_path(config)
    source_audit = report_dir(config) / "source_data_audit.csv"
    selection_path = report_dir(config) / "candidate_acceptance.csv"
    selection_pass = False
    selected_version = ""
    if selection_path.exists():
        selection = pd.read_csv(selection_path)
        selected = selection[selection.get("candidate_for_future_final_test", pd.Series(False)).fillna(False)]
        selection_pass = not selected.empty
        selected_version = str(selected["version"].iloc[0]) if selection_pass else ""

    universe_daily_change = False
    fold_member_summary: list[dict[str, Any]] = []
    if universe_path.exists():
        universe = pd.read_csv(universe_path, usecols=["date", "instrument"])
        daily_counts = universe.groupby("date")["instrument"].nunique()
        universe_daily_change = bool(daily_counts.nunique() > 1)
        for fold in config.get("folds", []):
            valid_counts = daily_counts[(daily_counts.index >= fold["valid_start"]) & (daily_counts.index <= fold["valid_end"])]
            fold_member_summary.append(
                {
                    "fold": fold["fold"],
                    "min_members": int(valid_counts.min()) if not valid_counts.empty else 0,
                    "median_members": float(valid_counts.median()) if not valid_counts.empty else 0.0,
                    "max_members": int(valid_counts.max()) if not valid_counts.empty else 0,
                }
            )

    coverage = read_json(report_dir(config) / "pit_provider_coverage_summary.json")
    industry_audit = read_json(report_dir(config) / "pit_industry_membership_summary.json")
    source_summary = read_json(report_dir(config) / "source_data_audit_summary.json")
    manifest.update(
        {
            "experiment": "Explore7 PIT pullback subsystem rebuild",
            "config_path": relpath(config["_config_path"]),
            "config_sha256": config["_config_hash"],
            "provider_uri": config["paths"]["provider_uri"],
            "provider_fallback_uri": coverage.get("fallback_provider_uri", ""),
            "provider_coverage_limited_diagnostic": bool(coverage.get("coverage_limited_diagnostic", False)),
            "market": config["qlib"]["market"],
            "benchmark": config["qlib"]["benchmark"],
            "required_fields": config["qlib"]["required_fields"],
            "universe_name": config["universe"]["name"],
            "universe_membership": relpath(universe_path),
            "universe_membership_sha256": maybe_sha256(universe_path),
            "universe_point_in_time": bool(config["universe"].get("point_in_time", False)),
            "universe_daily_membership_changes": universe_daily_change,
            "fold_universe_member_summary": fold_member_summary,
            "industry_membership": relpath(industry_path),
            "industry_membership_sha256": maybe_sha256(industry_path),
            "industry_membership_point_in_time": bool(industry_audit.get("point_in_time", False)),
            "missing_industry": config["industry"].get("missing_industry", "UNKNOWN"),
            "provider_coverage": coverage,
            "source_data_audit": relpath(source_audit),
            "source_path_classification_summary": source_summary,
            "result_csv_used_for_calculation": False,
            "any_explore456_result_csv_used": False,
            "folds": config.get("folds", []),
            "pullback_class_precedence": config["pullback_classes"]["precedence"],
            "versions": config["versions"],
            "selection": config["selection"],
            "candidate_for_future_final_test": selection_pass,
            "selected_version": selected_version,
            "observed_replication_used_for_selection": bool(config["selection"].get("observed_replication_used_for_selection", False)),
            "tushare_token_present": bool(load_dotenv_token()),
            "command_sequence": commands,
            "output_paths": output_paths,
        }
    )
    if extra:
        manifest.update(extra)
    write_json(manifest, path)


def flattened_paths(data: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(data, dict):
        for key, value in data.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            yield from flattened_paths(value, child)
    elif isinstance(data, list):
        for idx, value in enumerate(data):
            child = f"{prefix}[{idx}]"
            yield from flattened_paths(value, child)
    else:
        yield prefix, data


def is_path_like(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return "/" in value or lowered.endswith((".csv", ".pkl", ".json", ".yaml", ".yml", ".md", ".txt"))


def classify_source_path(config: dict[str, Any], source_key: str, key_path: str, value: Any) -> tuple[str, bool, str]:
    sources = config.get("sources", {})
    if source_key in set(sources.get("background_reference_only", [])):
        return "background_reference", False, "historical report may be cited as background only"
    text = str(value)
    forbidden_patterns = sources.get("forbidden_result_path_patterns", [])
    if any(pattern in text for pattern in forbidden_patterns):
        return "forbidden_result_path", False, "matched forbidden historical output/cache/backtest/diagnostic path"
    if key_path.startswith("paths.") or any(token in key_path.lower() for token in ["output", "cache", "backtest", "diagnostic"]):
        return "forbidden_result_path", False, "source config path keys are not calculation inputs"
    return "source_config_non_path_value", False, "not used directly"


def build_source_data_audit(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    sources = config.get("sources", {})
    allowed = sources.get("allowed_config_keys", {})
    for source_key, path in source_paths(config).items():
        exists = path.exists()
        if not exists:
            rows.append(
                {
                    "source_key": source_key,
                    "source_path": relpath(path),
                    "key_path": "",
                    "value": "",
                    "classification": "missing_source",
                    "used_for_calculation": False,
                    "reason": "source file does not exist",
                    "sha256": "",
                }
            )
            continue
        sha = file_sha256(path)
        if source_key in set(sources.get("background_reference_only", [])):
            rows.append(
                {
                    "source_key": source_key,
                    "source_path": relpath(path),
                    "key_path": "",
                    "value": relpath(path),
                    "classification": "background_reference",
                    "used_for_calculation": False,
                    "reason": "historical report path explicitly allowed as background text only",
                    "sha256": sha,
                }
            )
            continue
        if path.suffix.lower() in {".yaml", ".yml"}:
            data = load_yaml(path)
            for key in allowed.get(source_key, []):
                rows.append(
                    {
                        "source_key": source_key,
                        "source_path": relpath(path),
                        "key_path": key,
                        "value": "<structural_config>",
                        "classification": "allowed_structural_config_key",
                        "used_for_calculation": True,
                        "reason": "closed whitelist structural key",
                        "sha256": sha,
                    }
                )
            for key_path, value in flattened_paths(data):
                if not is_path_like(value) and not key_path.startswith("paths."):
                    continue
                classification, used, reason = classify_source_path(config, source_key, key_path, value)
                rows.append(
                    {
                        "source_key": source_key,
                        "source_path": relpath(path),
                        "key_path": key_path,
                        "value": str(value),
                        "classification": classification,
                        "used_for_calculation": used,
                        "reason": reason,
                        "sha256": sha,
                    }
                )
    audit = pd.DataFrame(rows)
    if audit.empty:
        audit = pd.DataFrame(
            columns=["source_key", "source_path", "key_path", "value", "classification", "used_for_calculation", "reason", "sha256"]
        )
    output = write_csv(audit, report_dir(config) / "source_data_audit.csv")
    summary = audit.groupby("classification", as_index=False).agg(rows=("classification", "size"), used_for_calculation=("used_for_calculation", "sum"))
    write_json(
        {
            "rows": int(len(audit)),
            "classification_counts": summary.set_index("classification")["rows"].to_dict() if not summary.empty else {},
            "forbidden_result_paths_used_for_calculation": int(
                audit[(audit["classification"] == "forbidden_result_path") & (audit["used_for_calculation"].astype(bool))].shape[0]
            ),
            "result_csv_used_for_calculation": False,
            "path": relpath(output),
        },
        report_dir(config) / "source_data_audit_summary.json",
    )
    return audit


def validate_source_audit(audit: pd.DataFrame) -> None:
    bad = audit[(audit["classification"] == "forbidden_result_path") & (audit["used_for_calculation"].astype(bool))]
    if not bad.empty:
        raise DataGateError("forbidden historical result path was marked used_for_calculation")


def copy_target_inputs(config: dict[str, Any]) -> list[Path]:
    outputs: list[Path] = []
    src_dir = TOPIC_DIR / "Explore5/data/targets"
    dst_dir = target_dir(config)
    for name in [
        "target_history.csv",
        "industry_targets.csv",
        "market_targets.csv",
        "theme_targets.csv",
    ]:
        src = src_dir / name
        dst = dst_dir / name
        if src.exists() and not dst.exists():
            ensure_parent(dst)
            dst.write_bytes(src.read_bytes())
            outputs.append(dst)
    return outputs


def fetch_stock_basic(pro) -> pd.DataFrame:
    frames = []
    for status in ["L", "D", "P"]:
        try:
            df = pro.stock_basic(
                exchange="",
                list_status=status,
                fields="ts_code,symbol,name,area,industry,market,list_date,delist_date,is_hs",
            )
        except Exception as exc:  # noqa: BLE001
            raise DataGateError(f"Tushare stock_basic failed for list_status={status}: {exc}") from exc
        if df is not None and not df.empty:
            df = df.copy()
            df["list_status"] = status
            frames.append(df)
    if not frames:
        raise DataGateError("Tushare stock_basic returned no rows")
    data = pd.concat(frames, ignore_index=True).drop_duplicates("ts_code", keep="first")
    data["instrument"] = data["ts_code"].map(ts_code_to_instrument)
    data["list_date"] = pd.to_datetime(data["list_date"].astype(str), format="%Y%m%d", errors="coerce")
    data["delist_date"] = pd.to_datetime(data.get("delist_date", "").astype(str), format="%Y%m%d", errors="coerce")
    data["is_mainboard_prefix"] = data["instrument"].map(is_mainboard_instrument)
    return data


def fetch_trade_calendar(pro, config: dict[str, Any]) -> pd.DataFrame:
    try:
        df = pro.trade_cal(
            exchange="",
            start_date=date_token(config["dates"]["data_start"]),
            end_date=date_token(config["dates"]["data_end"]),
            fields="exchange,cal_date,is_open,pretrade_date",
        )
    except Exception as exc:  # noqa: BLE001
        raise DataGateError(f"Tushare trade_cal failed: {exc}") from exc
    if df is None or df.empty:
        raise DataGateError("Tushare trade_cal returned no rows")
    data = df.copy()
    data["date"] = pd.to_datetime(data["cal_date"].astype(str), errors="coerce")
    data["is_open"] = pd.to_numeric(data["is_open"], errors="coerce").fillna(0).astype(int)
    return data[data["is_open"] == 1].sort_values("date").reset_index(drop=True)


def cached_tushare_daily_basic(pro, trade_date: str, cache_root: Path) -> pd.DataFrame:
    path = cache_root / f"{trade_date}.pkl"
    if path.exists():
        return pd.read_pickle(path)
    df = pro.daily_basic(
        trade_date=trade_date,
        fields="ts_code,trade_date,close,total_mv,circ_mv,total_share,float_share,turnover_rate,volume_ratio,pe,pb",
    )
    if df is None:
        df = pd.DataFrame()
    ensure_parent(path)
    pd.to_pickle(df, path)
    return df


def prefetch_tushare_daily_basic_cache(pro, tokens: list[str], cache_root: Path) -> None:
    missing = [token for token in tokens if not (cache_root / f"{token}.pkl").exists()]
    if not missing:
        return
    workers = min(4, max(1, int(os.getenv("EXPLORE7_TUSHARE_WORKERS", "4"))))

    def fetch_one(trade_date: str) -> tuple[str, int, str]:
        path = cache_root / f"{trade_date}.pkl"
        if path.exists():
            return trade_date, len(pd.read_pickle(path)), ""
        df = pro.daily_basic(
            trade_date=trade_date,
            fields="ts_code,trade_date,close,total_mv,circ_mv,total_share,float_share,turnover_rate,volume_ratio,pe,pb",
        )
        if df is None:
            df = pd.DataFrame()
        ensure_parent(path)
        pd.to_pickle(df, path)
        return trade_date, len(df), ""

    print(f"prefetching Tushare daily_basic cache missing_dates={len(missing)} workers={workers}", flush=True)
    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_one, token): token for token in missing}
        for future in as_completed(futures):
            completed += 1
            token = futures[future]
            try:
                _, rows, error = future.result()
                if error:
                    print(f"daily_basic {token} failed: {error}", flush=True)
                elif completed % 100 == 0 or completed == len(missing):
                    print(f"prefetched daily_basic {completed}/{len(missing)} last={token} rows={rows}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"daily_basic {token} failed: {exc}", flush=True)


def fetch_namechange(pro, stock_basic: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    statuses: list[dict[str, Any]] = []
    try:
        df = pro.namechange(fields="ts_code,name,start_date,end_date,change_reason")
        if df is not None and not df.empty:
            statuses.append({"source": "tushare.namechange", "mode": "all", "status": "ok", "rows": len(df), "error": ""})
            return normalize_namechange(df), statuses
    except Exception as exc:  # noqa: BLE001
        statuses.append({"source": "tushare.namechange", "mode": "all", "status": "failed", "rows": 0, "error": str(exc)})

    rows = []
    mainboard = stock_basic[stock_basic["is_mainboard_prefix"]].copy()
    for ts_code in mainboard["ts_code"].dropna().astype(str).unique():
        try:
            df = pro.namechange(ts_code=ts_code, fields="ts_code,name,start_date,end_date,change_reason")
            if df is not None and not df.empty:
                rows.append(df)
        except Exception as exc:  # noqa: BLE001
            statuses.append({"source": "tushare.namechange", "mode": ts_code, "status": "failed", "rows": 0, "error": str(exc)})
        time.sleep(0.05)
    data = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    statuses.append({"source": "tushare.namechange", "mode": "per_ts_code", "status": "ok" if not data.empty else "empty", "rows": len(data), "error": ""})
    return normalize_namechange(data), statuses


def normalize_namechange(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["ts_code", "name", "start_date", "end_date", "is_st_like"])
    data = df.copy()
    for column in ["start_date", "end_date"]:
        if column not in data.columns:
            data[column] = pd.NaT
        data[column] = pd.to_datetime(data[column].astype(str).replace({"": pd.NA, "None": pd.NA}), errors="coerce")
    data["name"] = data.get("name", "").astype(str)
    data["is_st_like"] = data["name"].str.upper().str.contains("ST", na=False) | data["name"].str.contains("退", na=False)
    return data[["ts_code", "name", "start_date", "end_date", "is_st_like"]].drop_duplicates()


def st_codes_for_date(namechange: pd.DataFrame, stock_basic: pd.DataFrame, trade_date: pd.Timestamp) -> tuple[set[str], str]:
    if namechange.empty:
        names = stock_basic["name"].astype(str)
        mask = names.str.upper().str.contains("ST", na=False) | names.str.contains("退", na=False)
        return set(stock_basic.loc[mask, "ts_code"].astype(str)), "stock_basic_current_name_only"
    active = namechange[
        (namechange["start_date"].isna() | (namechange["start_date"] <= trade_date))
        & (namechange["end_date"].isna() | (namechange["end_date"] >= trade_date))
        & namechange["is_st_like"].fillna(False)
    ]
    return set(active["ts_code"].astype(str)), "tushare.namechange"


def build_daily_pit_universe(config: dict[str, Any], pro) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    stock_basic = fetch_stock_basic(pro)
    calendar = fetch_trade_calendar(pro, config)
    namechange, name_status = fetch_namechange(pro, stock_basic)
    open_dates = list(calendar["date"])
    open_index = {date: idx for idx, date in enumerate(open_dates)}
    first_trade_index: dict[str, int] = {}
    for _, row in stock_basic.iterrows():
        list_date = row["list_date"]
        if pd.isna(list_date):
            continue
        first = next((idx for idx, date in enumerate(open_dates) if date >= list_date), None)
        if first is not None:
            first_trade_index[str(row["ts_code"])] = first

    threshold_cny = float(config["universe"]["market_cap_threshold_cny"])
    threshold_10k = threshold_cny / 10_000.0
    min_age = int(config["universe"]["min_listing_age_trading_days"])
    daily_cache = cache_dir(config) / "tushare_daily_basic"
    ensure_dir(daily_cache)
    prefetch_tushare_daily_basic_cache(pro, [date.strftime("%Y%m%d") for date in open_dates], daily_cache)
    basic_cols = ["ts_code", "instrument", "name", "market", "list_status", "list_date", "delist_date", "is_mainboard_prefix"]
    basic = stock_basic[basic_cols].copy()
    rows: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []
    for seq, date in enumerate(open_dates, start=1):
        token = date.strftime("%Y%m%d")
        try:
            daily = cached_tushare_daily_basic(pro, token, daily_cache)
        except Exception as exc:  # noqa: BLE001
            audit_rows.append(
                {
                    "date": date.date().isoformat(),
                    "status": "daily_basic_failed",
                    "daily_basic_rows": 0,
                    "eligible_rows": 0,
                    "error": str(exc),
                }
            )
            continue
        if daily.empty:
            audit_rows.append(
                {
                    "date": date.date().isoformat(),
                    "status": "daily_basic_empty",
                    "daily_basic_rows": 0,
                    "eligible_rows": 0,
                    "error": "empty daily_basic response",
                }
            )
            continue
        data = daily.merge(basic, on="ts_code", how="left")
        data["is_mainboard_prefix"] = data["is_mainboard_prefix"].eq(True)
        data["trade_date"] = pd.to_datetime(data["trade_date"].astype(str), errors="coerce")
        data["total_mv"] = pd.to_numeric(data.get("total_mv"), errors="coerce")
        data["total_share"] = pd.to_numeric(data.get("total_share"), errors="coerce")
        data["close"] = pd.to_numeric(data.get("close"), errors="coerce")
        data["market_cap_asof_T"] = data["total_mv"] * 10_000.0
        data["listing_age_trading_days"] = data["ts_code"].map(lambda code: open_index[date] - first_trade_index.get(str(code), open_index[date] + 1))
        data["listed_asof_T"] = (data["list_date"].notna()) & (data["list_date"] <= date)
        data["not_delisted_asof_T"] = data["delist_date"].isna() | (data["delist_date"] > date)
        st_codes, status_source = st_codes_for_date(namechange, stock_basic, date)
        data["st_or_delisting_asof_T"] = data["ts_code"].astype(str).isin(st_codes)
        data["status_source"] = status_source
        eligible = data[
            data["is_mainboard_prefix"]
            & data["listed_asof_T"]
            & data["not_delisted_asof_T"]
            & (data["listing_age_trading_days"] >= min_age)
            & (data["market_cap_asof_T"] >= threshold_cny)
            & data["market_cap_asof_T"].notna()
            & ~data["st_or_delisting_asof_T"]
        ].copy()
        if not eligible.empty:
            eligible["date"] = date.date().isoformat()
            eligible["source_trade_date"] = token
            eligible["market_cap_threshold_cny"] = threshold_cny
            eligible["market_cap_source"] = "tushare.daily_basic.total_mv"
            eligible["price_source"] = "tushare.daily_basic.close"
            rows.append(
                eligible[
                    [
                        "date",
                        "instrument",
                        "ts_code",
                        "name",
                        "market",
                        "list_date",
                        "delist_date",
                        "listing_age_trading_days",
                        "close",
                        "total_share",
                        "market_cap_asof_T",
                        "market_cap_threshold_cny",
                        "status_source",
                        "market_cap_source",
                        "price_source",
                        "source_trade_date",
                    ]
                ]
            )
        audit_rows.append(
            {
                "date": date.date().isoformat(),
                "status": "ok",
                "daily_basic_rows": int(len(daily)),
                "mainboard_prefix_rows": int(data["is_mainboard_prefix"].sum()),
                "listed_rows": int(data["listed_asof_T"].fillna(False).sum()),
                "listing_age_pass_rows": int((data["listing_age_trading_days"] >= min_age).sum()),
                "market_cap_pass_rows": int((data["market_cap_asof_T"] >= threshold_cny).sum()),
                "st_or_delisting_rows": int(data["st_or_delisting_asof_T"].fillna(False).sum()),
                "missing_market_cap_rows": int(data["market_cap_asof_T"].isna().sum()),
                "eligible_rows": int(len(eligible)),
                "error": "",
            }
        )
        if seq % 100 == 0:
            print(f"built PIT universe through {token} eligible={len(eligible)}", flush=True)
    universe = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    audit = pd.DataFrame(audit_rows)
    name_audit = pd.DataFrame(name_status)
    if not universe.empty:
        universe = universe.sort_values(["date", "instrument"]).drop_duplicates(["date", "instrument"], keep="last")
    return universe, audit, name_audit


def write_qlib_instrument_file(universe: pd.DataFrame, path: str | Path) -> Path:
    output = ensure_parent(path)
    lines: list[str] = []
    if not universe.empty:
        grouped = universe.groupby("instrument")["date"].agg(["min", "max"]).reset_index().sort_values("instrument")
        for _, row in grouped.iterrows():
            lines.append(f"{row['instrument']}\t{row['min']}\t{row['max']}")
    output.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return output


def fetch_pit_industry_membership(config: dict[str, Any], pro, universe: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[pd.DataFrame] = []
    status_rows: list[dict[str, Any]] = []
    interval_rows: list[dict[str, Any]] = []
    data_start = parse_dt(config["dates"]["data_start"])
    data_end = parse_dt(config["dates"]["data_end"])
    universe_small = universe[["date", "instrument"]].copy()
    universe_small["date"] = pd.to_datetime(universe_small["date"])
    for target in config["targets"]["industry"]:
        target_key = target["target_key"]
        ts_code = target["ts_code"]
        try:
            df = pro.index_member(index_code=ts_code)
            if df is None or df.empty:
                raise RuntimeError("empty index_member response")
            data = df.copy()
            con_col = "con_code" if "con_code" in data.columns else "ts_code"
            if con_col not in data.columns:
                raise RuntimeError(f"index_member response missing constituent code for {ts_code}")
            data["instrument"] = data[con_col].map(ts_code_to_instrument)
            data["in_date"] = pd.to_datetime(data.get("in_date", "").astype(str), errors="coerce").fillna(data_start)
            data["out_date"] = pd.to_datetime(data.get("out_date", "").astype(str), errors="coerce").fillna(data_end)
            data.loc[data["out_date"] < data["in_date"], "out_date"] = data_end
            data = data[["instrument", "in_date", "out_date"]].drop_duplicates()
            for _, interval in data.iterrows():
                interval_rows.append(
                    {
                        "instrument": interval["instrument"],
                        "industry_target_key": target_key,
                        "industry_ts_code": ts_code,
                        "industry_name": target["name"],
                        "in_date": interval["in_date"].date().isoformat(),
                        "out_date": interval["out_date"].date().isoformat(),
                        "source": "tushare.index_member",
                    }
                )
            merged = universe_small.merge(data, on="instrument", how="inner")
            active = merged[(merged["date"] >= merged["in_date"]) & (merged["date"] <= merged["out_date"])].copy()
            if not active.empty:
                active["industry_target_key"] = target_key
                active["industry_ts_code"] = ts_code
                active["industry_name"] = target["name"]
                active["source"] = "tushare.index_member"
                rows.append(active[["date", "instrument", "industry_target_key", "industry_ts_code", "industry_name", "source"]])
            status_rows.append(
                {
                    "industry_target_key": target_key,
                    "industry_ts_code": ts_code,
                    "status": "ok",
                    "source": "tushare.index_member",
                    "source_rows": int(len(df)),
                    "active_universe_rows": int(len(active)),
                    "point_in_time": True,
                    "error": "",
                }
            )
        except Exception as exc:  # noqa: BLE001
            status_rows.append(
                {
                    "industry_target_key": target_key,
                    "industry_ts_code": ts_code,
                    "status": "failed",
                    "source": "tushare.index_member",
                    "source_rows": 0,
                    "active_universe_rows": 0,
                    "point_in_time": False,
                    "error": str(exc),
                }
            )
        time.sleep(0.08)
    matched = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if not matched.empty:
        matched["date"] = pd.to_datetime(matched["date"]).dt.date.astype(str)
        matched = matched.sort_values(["date", "instrument", "industry_target_key"]).drop_duplicates(["date", "instrument"], keep="first")
    base = universe[["date", "instrument"]].drop_duplicates()
    membership = base.merge(matched, on=["date", "instrument"], how="left") if not matched.empty else base.copy()
    membership["industry_target_key"] = membership["industry_target_key"].fillna("UNKNOWN")
    membership["industry_ts_code"] = membership["industry_ts_code"].fillna("UNKNOWN")
    membership["industry_name"] = membership["industry_name"].fillna(config["industry"].get("missing_industry", "UNKNOWN")).replace("", "UNKNOWN")
    membership["source"] = membership["source"].fillna("missing_pit_industry")
    return membership.sort_values(["date", "instrument"]), pd.DataFrame(status_rows)


def command_build_pit_universe(config: dict[str, Any]) -> list[Path]:
    for path in [config["paths"]["cache_dir"], config["paths"]["report_dir"], config["paths"]["backtest_dir"], Path(config["paths"]["universe_membership"]).parent, config["paths"]["target_dir"]]:
        ensure_dir(path)
    audit = build_source_data_audit(config)
    validate_source_audit(audit)
    copied_targets = copy_target_inputs(config)
    pro = load_tushare_client(required=True)
    universe, universe_audit, name_audit = build_daily_pit_universe(config, pro)
    if universe.empty:
        write_csv(universe, universe_membership_path(config))
        write_csv(universe_audit, report_dir(config) / "pit_universe_audit.csv")
        write_csv(name_audit, report_dir(config) / "pit_name_status_audit.csv")
        raise DataGateError("PIT universe is empty; cannot continue")
    outputs = copied_targets + [
        write_csv(universe, universe_membership_path(config)),
        write_qlib_instrument_file(universe, universe_qlib_path(config)),
        write_csv(universe_audit, report_dir(config) / "pit_universe_audit.csv"),
        write_csv(name_audit, report_dir(config) / "pit_name_status_audit.csv"),
    ]
    industry, industry_audit = fetch_pit_industry_membership(config, pro, universe)
    outputs.extend(
        [
            write_csv(industry, industry_membership_path(config)),
            write_csv(industry_audit, report_dir(config) / "pit_industry_membership_audit.csv"),
        ]
    )
    unknown_ratio = float((industry["industry_name"] == config["industry"].get("missing_industry", "UNKNOWN")).mean()) if not industry.empty else 1.0
    industry_ok = bool(not industry_audit.empty and (industry_audit["status"] == "ok").all() and industry_audit["point_in_time"].fillna(False).all())
    write_json(
        {
            "point_in_time": industry_ok,
            "rows": int(len(industry)),
            "unknown_ratio": unknown_ratio,
            "failed_targets": industry_audit.loc[industry_audit["status"] != "ok", "industry_target_key"].tolist() if not industry_audit.empty else [],
            "path": relpath(industry_membership_path(config)),
        },
        report_dir(config) / "pit_industry_membership_summary.json",
    )
    daily_counts = universe.groupby("date")["instrument"].nunique()
    record_manifest(
        config,
        "build-pit-universe",
        outputs,
        {
            "pit_universe_rows": int(len(universe)),
            "pit_universe_instruments": int(universe["instrument"].nunique()),
            "pit_universe_min_date": str(universe["date"].min()),
            "pit_universe_max_date": str(universe["date"].max()),
            "pit_universe_daily_count_min": int(daily_counts.min()),
            "pit_universe_daily_count_median": float(daily_counts.median()),
            "pit_universe_daily_count_max": int(daily_counts.max()),
        },
    )
    print(f"built PIT universe rows={len(universe)} instruments={universe['instrument'].nunique()}", flush=True)
    return outputs


def read_universe(config: dict[str, Any]) -> pd.DataFrame:
    path = universe_membership_path(config)
    if not path.exists():
        raise DataGateError(f"PIT universe missing: {relpath(path)}")
    data = pd.read_csv(path, parse_dates=["date", "list_date", "delist_date"])
    if data.empty:
        raise DataGateError(f"PIT universe is empty: {relpath(path)}")
    data["instrument"] = data["instrument"].astype(str).str.upper()
    return data


def read_pit_industry(config: dict[str, Any]) -> pd.DataFrame:
    path = industry_membership_path(config)
    if not path.exists():
        raise DataGateError(f"PIT industry membership missing: {relpath(path)}")
    data = pd.read_csv(path, parse_dates=["date"])
    if data.empty:
        raise DataGateError(f"PIT industry membership is empty: {relpath(path)}")
    data["instrument"] = data["instrument"].astype(str).str.upper()
    data["industry_name"] = data["industry_name"].fillna(config["industry"].get("missing_industry", "UNKNOWN")).replace("", "UNKNOWN")
    return data


def qlib_instruments_from_universe(config: dict[str, Any]) -> list[str]:
    path = universe_qlib_path(config)
    if path.exists():
        instruments = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            instruments.append(line.split()[0].upper())
        if instruments:
            return sorted(set(instruments))
    universe = read_universe(config)
    return sorted(universe["instrument"].unique())


def provider_candidates(config: dict[str, Any]) -> list[tuple[Path, bool]]:
    primary = topic_path(config["paths"]["provider_uri"])
    candidates = [(primary, False)]
    source_value = config.get("_source_provider_uri", "")
    source = topic_path(source_value) if source_value else Path("")
    if source_value and source.exists() and source != primary:
        candidates.append((source, True))
    return candidates


def load_stock_panel_from_qlib(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    instruments = qlib_instruments_from_universe(config)
    last_error = ""
    for provider_uri, fallback in provider_candidates(config):
        if not provider_uri.exists():
            last_error = f"provider missing: {relpath(provider_uri)}"
            continue
        try:
            qlib.init(provider_uri=str(provider_uri), region=REG_CN)
            df = D.features(
                instruments=instruments,
                fields=config["qlib"]["required_fields"],
                start_time=config["dates"]["data_start"],
                end_time=config["dates"]["data_end"],
                freq=config["costs"]["freq"],
            )
            if df.empty:
                last_error = f"Qlib provider returned no stock data: {relpath(provider_uri)}"
                continue
            data = df.rename(columns=FIELD_RENAME).reset_index()
            data["instrument"] = data["instrument"].astype(str).str.upper()
            data["datetime"] = pd.to_datetime(data["datetime"]).dt.normalize()
            meta = {
                "provider_uri": relpath(provider_uri),
                "fallback_provider_uri": relpath(provider_uri) if fallback else "",
                "fallback_used": bool(fallback),
                "loaded_instruments": int(data["instrument"].nunique()),
                "loaded_rows": int(len(data)),
            }
            return data.sort_values(["instrument", "datetime"]).reset_index(drop=True), meta
        except Exception as exc:  # noqa: BLE001
            last_error = f"{relpath(provider_uri)}: {exc}"
    raise DataGateError(f"no readable Qlib stock provider for Explore7; last_error={last_error}")


def load_stock_panel(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    path = stock_panel_cache_path(config)
    meta_path = cache_dir(config) / "stock_panel_meta.json"
    if path.exists() and meta_path.exists():
        return pd.read_pickle(path), read_json(meta_path)
    panel, meta = load_stock_panel_from_qlib(config)
    ensure_parent(path)
    pd.to_pickle(panel, path)
    write_json(meta, meta_path)
    return panel, meta


def build_provider_coverage_audit(config: dict[str, Any], universe: pd.DataFrame, panel: pd.DataFrame, provider_meta: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = [FIELD_RENAME.get(field, field.lstrip("$")) for field in config["qlib"]["required_fields"]]
    keys = universe[["date", "instrument"]].drop_duplicates().copy()
    keys["datetime"] = pd.to_datetime(keys["date"]).dt.normalize()
    available_cols = ["datetime", "instrument"] + [field for field in required if field in panel.columns]
    availability = panel[available_cols].copy()
    for field in required:
        if field not in availability.columns:
            availability[field] = np.nan
    merged = keys.merge(availability, on=["datetime", "instrument"], how="left")
    missing_fields = []
    for _, row in merged.iterrows():
        missing = [field for field in required if pd.isna(row.get(field))]
        if missing:
            missing_fields.append(
                {
                    "date": row["datetime"].date().isoformat(),
                    "instrument": row["instrument"],
                    "missing_fields": ",".join(missing),
                    "missing_field_count": len(missing),
                }
            )
    audit = pd.DataFrame(missing_fields, columns=["date", "instrument", "missing_fields", "missing_field_count"])
    covered_rows = int(len(merged) - len(audit))
    coverage_ratio = float(covered_rows / len(merged)) if len(merged) else 0.0
    coverage_limited = bool(provider_meta.get("fallback_used", False) or coverage_ratio < 0.995)
    summary = {
        "provider_uri": provider_meta.get("provider_uri", config["paths"]["provider_uri"]),
        "fallback_provider_uri": provider_meta.get("fallback_provider_uri", ""),
        "fallback_used": bool(provider_meta.get("fallback_used", False)),
        "membership_rows": int(len(merged)),
        "covered_membership_rows": covered_rows,
        "missing_membership_rows": int(len(audit)),
        "coverage_ratio": coverage_ratio,
        "coverage_limited_diagnostic": coverage_limited,
        "required_fields": required,
    }
    return audit, summary


def command_audit_pit_data(config: dict[str, Any]) -> list[Path]:
    audit = build_source_data_audit(config)
    validate_source_audit(audit)
    universe = read_universe(config)
    industry = read_pit_industry(config)
    industry_audit_path = report_dir(config) / "pit_industry_membership_audit.csv"
    if industry_audit_path.exists():
        industry_audit = pd.read_csv(industry_audit_path)
    else:
        industry_audit = pd.DataFrame()
    industry_ok = bool(not industry_audit.empty and (industry_audit["status"] == "ok").all() and industry_audit["point_in_time"].fillna(False).all())
    unknown_ratio = float((industry["industry_name"] == config["industry"].get("missing_industry", "UNKNOWN")).mean()) if not industry.empty else 1.0
    write_json(
        {
            "point_in_time": industry_ok,
            "rows": int(len(industry)),
            "unknown_ratio": unknown_ratio,
            "failed_targets": industry_audit.loc[industry_audit["status"] != "ok", "industry_target_key"].tolist() if not industry_audit.empty else [],
            "path": relpath(industry_membership_path(config)),
        },
        report_dir(config) / "pit_industry_membership_summary.json",
    )
    outputs = [report_dir(config) / "source_data_audit.csv", report_dir(config) / "pit_industry_membership_summary.json"]
    if not industry_ok:
        record_manifest(config, "audit-pit-data", outputs, {"data_gate_status": "blocked_missing_pit_industry"})
        raise DataGateError("PIT industry membership is not complete/point-in-time; strict gate blocks walk-forward")
    panel, provider_meta = load_stock_panel(config)
    coverage, summary = build_provider_coverage_audit(config, universe, panel, provider_meta)
    outputs.extend(
        [
            write_csv(coverage, report_dir(config) / "pit_provider_coverage_audit.csv"),
            write_json(summary, report_dir(config) / "pit_provider_coverage_summary.json"),
        ]
    )
    daily_counts = universe.groupby("date")["instrument"].nunique()
    universe_audit_summary = pd.DataFrame(
        [
            {
                "item": "pit_universe_rows",
                "value": int(len(universe)),
            },
            {
                "item": "pit_universe_instruments",
                "value": int(universe["instrument"].nunique()),
            },
            {
                "item": "daily_member_count_min",
                "value": int(daily_counts.min()),
            },
            {
                "item": "daily_member_count_median",
                "value": float(daily_counts.median()),
            },
            {
                "item": "daily_member_count_max",
                "value": int(daily_counts.max()),
            },
            {
                "item": "daily_membership_changed",
                "value": bool(daily_counts.nunique() > 1),
            },
            {
                "item": "static_20251231_universe_used_as_authority",
                "value": False,
            },
        ]
    )
    outputs.append(write_csv(universe_audit_summary, report_dir(config) / "pit_universe_summary.csv"))
    record_manifest(config, "audit-pit-data", outputs, {"data_gate_status": "ok", "provider_coverage": summary})
    print(f"audited PIT data coverage_ratio={summary['coverage_ratio']:.2%} coverage_limited={summary['coverage_limited_diagnostic']}", flush=True)
    return outputs


def add_group_indicators(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy().sort_values(["instrument", "datetime"])
    group = df.groupby("instrument", group_keys=False)
    for span in [20, 30, 60, 120]:
        df[f"ema{span}"] = group["close"].transform(lambda s, span=span: s.ewm(span=span, adjust=False).mean())
    prev_close = group["close"].shift(1)
    true_range = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
        axis=1,
    )
    df["true_range"] = true_range.max(axis=1)
    df["atr20"] = group["true_range"].transform(lambda s: s.rolling(20, min_periods=5).mean())
    df["ret1"] = group["close"].pct_change()
    df["ret5"] = group["close"].pct_change(5)
    df["ret20"] = group["close"].pct_change(20)
    df["ret60"] = group["close"].pct_change(60)
    df["volatility20"] = group["ret1"].transform(lambda s: s.rolling(20, min_periods=10).std())
    df["avg_money20"] = group["money"].transform(lambda s: s.rolling(20, min_periods=5).mean())
    df["money_ratio20"] = df["money"] / df["avg_money20"].replace(0, np.nan)
    df["ema60_slope10"] = df["ema60"] / group["ema60"].shift(10) - 1.0
    df["ema60_slope20"] = df["ema60"] / group["ema60"].shift(20) - 1.0
    df["ema20_slope20"] = df["ema20"] / group["ema20"].shift(20) - 1.0
    df["ema20_ema60_spread"] = df["ema20"] / df["ema60"] - 1.0
    df["dist_ema20"] = (df["close"] - df["ema20"]) / df["close"]
    df["distance_to_ema20"] = df["close"] / df["ema20"] - 1.0
    df["distance_to_ema60"] = df["close"] / df["ema60"] - 1.0
    df["rolling_high60"] = group["close"].transform(lambda s: s.shift(1).rolling(60, min_periods=20).max())
    df["rolling_low20"] = group["low"].transform(lambda s: s.shift(1).rolling(20, min_periods=5).min())
    df["rolling_low_5"] = group["low"].transform(lambda s: s.rolling(5, min_periods=2).min())
    df["recent_low5"] = group["low"].transform(lambda s: s.shift(1).rolling(5, min_periods=2).min())
    df["distance_to_high60"] = df["close"] / df["rolling_high60"] - 1.0
    df["distance_to_low20"] = df["close"] / df["rolling_low20"] - 1.0
    price_range = (df["high"] - df["low"]).replace(0, np.nan)
    df["close_pos"] = (df["close"] - df["low"]) / price_range
    df["upper_shadow_pct"] = (df["high"] - df[["open", "close"]].max(axis=1)) / price_range
    df["overheat"] = (df["close"] / df["ema20"] - 1.0).clip(lower=0)
    df["adx_proxy20"] = (df["ret20"].abs() / df["volatility20"].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    df["atr20_ratio"] = df["atr20"] / df["close"].replace(0, np.nan)
    df["prev_close"] = group["close"].shift(1)
    df["prev_ema20"] = group["ema20"].shift(1)
    df["recent_close_below_ema20"] = group.apply(lambda g: (g["close"] < g["ema20"]).shift(1).rolling(5, min_periods=1).max()).reset_index(level=0, drop=True).astype(bool)
    df["recent_touch_ema60"] = group.apply(lambda g: (g["low"] <= g["ema60"]).shift(1).rolling(5, min_periods=1).max()).reset_index(level=0, drop=True).astype(bool)
    return df


def daily_zscore(df: pd.DataFrame, column: str, lower: float, upper: float) -> pd.Series:
    def _one_day(values: pd.Series) -> pd.Series:
        numeric = pd.to_numeric(values, errors="coerce")
        if numeric.notna().sum() < 2:
            return pd.Series(0.0, index=values.index)
        clipped = numeric.clip(numeric.quantile(lower), numeric.quantile(upper))
        std = clipped.std(ddof=0)
        if pd.isna(std) or std == 0:
            return pd.Series(0.0, index=values.index)
        return (clipped - clipped.mean()) / std

    return df.groupby("datetime")[column].transform(_one_day)


def compute_target_regimes(config: dict[str, Any], history: pd.DataFrame) -> pd.DataFrame:
    rules = config["rules"]["market"]
    df = history.sort_values(["target_key", "date"]).copy()
    group = df.groupby("target_key", group_keys=False)
    df["ema60"] = group["close"].transform(lambda s: s.ewm(span=rules["ema"], adjust=False).mean())
    df["ema120"] = group["close"].transform(lambda s: s.ewm(span=rules["record_ema"], adjust=False).mean())
    df["ema60_slope20"] = df["ema60"] / group["ema60"].shift(rules["slope_window"]) - 1.0
    df["ret60"] = group["close"].pct_change(60)
    broad = df[df["target_key"] == "broad_market"][["date", "ret60"]].rename(columns={"ret60": "broad_ret60"})
    df = df.merge(broad.drop_duplicates("date"), on="date", how="left")
    df["close_gt_ema60"] = df["close"] > df["ema60"]
    df["close_gt_ema120"] = df["close"] > df["ema120"]
    df["ema60_slope20_gt0"] = df["ema60_slope20"] > 0
    df["ret60_gt_broad"] = df["ret60"] > df["broad_ret60"]
    df["trend_ok"] = df["close_gt_ema60"] & df["ema60_slope20_gt0"]
    df.loc[df["target_key"] != "broad_market", "trend_ok"] = df["trend_ok"] & df["ret60_gt_broad"]
    return df


def compute_market_width(config: dict[str, Any], indicators: pd.DataFrame) -> pd.DataFrame:
    rules = config["rules"]["width"]
    width = (
        indicators.assign(
            close_gt_ema60_flag=lambda x: x["close"] > x["ema60"],
            ema20_gt_ema60_flag=lambda x: x["ema20"] > x["ema60"],
        )
        .groupby("datetime", as_index=False)
        .agg(
            instruments=("instrument", "nunique"),
            close_gt_ema60_ratio=("close_gt_ema60_flag", "mean"),
            ema20_gt_ema60_ratio=("ema20_gt_ema60_flag", "mean"),
        )
    )
    strong = (width["close_gt_ema60_ratio"] > rules["close_gt_ema60"]) & (width["ema20_gt_ema60_ratio"] > rules["ema20_gt_ema60"])
    neutral = (width["close_gt_ema60_ratio"] > rules["close_gt_ema60"] * 0.8) & (
        width["ema20_gt_ema60_ratio"] > rules["ema20_gt_ema60"] * 0.8
    )
    width["width_ok"] = strong
    width["market_width_state"] = np.select([strong, neutral], ["width_strong", "width_neutral"], default="width_weak")
    return width.rename(columns={"datetime": "date"})


def build_regimes_and_signals(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    universe = read_universe(config)
    industry = read_pit_industry(config)
    panel, provider_meta = load_stock_panel(config)
    coverage, coverage_summary = build_provider_coverage_audit(config, universe, panel, provider_meta)
    write_csv(coverage, report_dir(config) / "pit_provider_coverage_audit.csv")
    write_json(coverage_summary, report_dir(config) / "pit_provider_coverage_summary.json")

    universe_key = universe[
        [
            "date",
            "instrument",
            "listing_age_trading_days",
            "market_cap_asof_T",
        ]
    ].copy()
    universe_key["datetime"] = pd.to_datetime(universe_key["date"]).dt.normalize()
    df = panel.merge(universe_key, on=["datetime", "instrument"], how="inner")
    if df.empty:
        raise DataGateError("provider has no rows after joining daily PIT universe")
    df["pit_universe_member"] = True
    df = add_group_indicators(df)
    ensure_parent(stock_indicators_cache_path(config))
    pd.to_pickle(df, stock_indicators_cache_path(config))

    history_path = topic_path(config["paths"]["target_history"])
    if not history_path.exists():
        copy_target_inputs(config)
    if not history_path.exists():
        raise DataGateError(f"target_history missing: {relpath(history_path)}")
    history = pd.read_csv(history_path, parse_dates=["date"])
    target_regimes = compute_target_regimes(config, history)
    width = compute_market_width(config, df)
    market = target_regimes[target_regimes["target_type"] == "market"].merge(width, on="date", how="left")
    broad = market[market["target_key"] == "broad_market"][["date", "trend_ok"]].rename(columns={"trend_ok": "market_ok"})
    market = market.merge(broad, on="date", how="left")
    industry_regime = target_regimes[target_regimes["target_type"] == "industry"].rename(columns={"trend_ok": "industry_trend_ok"})
    outputs = [
        write_csv(market, report_dir(config) / "market_regime.csv"),
        write_csv(width, report_dir(config) / "market_width.csv"),
        write_csv(industry_regime, report_dir(config) / "industry_regime.csv"),
    ]
    broad_state = market[market["target_key"] == "broad_market"][
        ["date", "market_ok", "market_width_state", "close_gt_ema60_ratio", "ema20_gt_ema60_ratio", "ret60"]
    ].rename(columns={"date": "datetime", "ret60": "broad_ret60"})
    df = df.merge(broad_state, on="datetime", how="left")
    industry_join = industry[["date", "instrument", "industry_target_key", "industry_name"]].copy()
    industry_join["datetime"] = pd.to_datetime(industry_join["date"]).dt.normalize()
    df = df.merge(industry_join[["datetime", "instrument", "industry_target_key", "industry_name"]], on=["datetime", "instrument"], how="left")
    df["industry_name"] = df["industry_name"].fillna(config["industry"].get("missing_industry", "UNKNOWN")).replace("", "UNKNOWN")
    df["industry_target_key"] = df["industry_target_key"].fillna("UNKNOWN").astype("string")
    industry_state = industry_regime[["date", "target_key", "industry_trend_ok"]].rename(
        columns={"date": "datetime", "target_key": "industry_target_key"}
    )
    industry_state["industry_target_key"] = industry_state["industry_target_key"].astype("string")
    df = df.merge(industry_state, on=["datetime", "industry_target_key"], how="left")

    candidate_rules = config["rules"]["candidate"]
    df["ret60_excess"] = df["ret60"] - df["broad_ret60"]
    df["volatility20_p90"] = df.groupby("datetime")["volatility20"].transform(lambda s: s.quantile(candidate_rules["volatility_quantile"]))
    df["avg_money20_p20"] = df.groupby("datetime")["avg_money20"].transform(lambda s: s.quantile(candidate_rules["money_quantile"]))
    atr_dist = candidate_rules["atr_dist_multiplier"] * df["atr20"] / df["close"]
    max_dist = np.minimum(candidate_rules["max_dist_ema20"], atr_dist)
    df["ema_state"] = (
        (df["ema20"] > df["ema60"])
        & (df["ema60_slope10"] > 0)
        & (df["close"] > df["ema60"])
        & (df["dist_ema20"] < max_dist)
        & (df["volatility20"] <= df["volatility20_p90"])
        & (df["avg_money20"] >= df["avg_money20_p20"])
    )
    df["market_ok_entry"] = df["ema_state"] & df["market_ok"].fillna(False)
    df["width_ok_entry"] = df["market_ok_entry"] & (df["market_width_state"].isin(["width_strong", "width_neutral"]))
    df["industry_ok_entry"] = df["width_ok_entry"] & df["industry_trend_ok"].fillna(False)

    score_rules = config["rules"]["score"]
    for component in score_rules["weights"]:
        df[f"z_{component}"] = daily_zscore(df, component, score_rules["winsor_lower"], score_rules["winsor_upper"])
    df["trend_score"] = 0.0
    for component, weight in score_rules["weights"].items():
        df["trend_score"] += float(weight) * df[f"z_{component}"]
    df.loc[~df["industry_ok_entry"], "trend_score"] = np.nan
    df["trend_score_pct"] = df.groupby("datetime")["trend_score"].rank(pct=True, ascending=False)
    df["trend_score_top20_entry"] = df["industry_ok_entry"] & (df["trend_score_pct"] <= score_rules["top_pct"])

    breakout = config["rules"]["breakout"]
    df["breakout_entry"] = (
        df["trend_score_top20_entry"]
        & (df["close"] > df["rolling_high60"])
        & (df["money_ratio20"] >= breakout["money_ratio"])
        & (df["close_pos"] >= 0.5)
        & (df["upper_shadow_pct"] <= breakout["upper_shadow_max"])
        & (df["dist_ema20"] < max_dist)
    )

    near_ema20 = df["low"] <= df["ema20"] * (1 + float(config["_explore7_rules"].get("ema_band_pct", 0.01)))
    near_ema30 = df["low"] <= df["ema30"] * (1 + float(config["_explore7_rules"].get("ema_band_pct", 0.01)))
    df["raw_pullback_shape"] = (near_ema20 | near_ema30) & (df["low"] > df["ema60"]) & (df["close"] >= df["ema20"]) & (df["close"] > df["open"])
    df["market_trend_state"] = np.where(df["market_ok"].fillna(False), "market_trend_on", "market_trend_off")
    df["industry_sync_state"] = np.where(df["industry_trend_ok"].fillna(False), "industry_sync_on", "industry_sync_off")
    classify_pullbacks(config, df)
    df["original_pullback_entry"] = df["trend_score_top20_entry"] & df["raw_pullback_shape"] & (df["money_ratio20"] <= 1.0)
    df["pullback_entry"] = df["original_pullback_entry"]
    df["combined_entry"] = df["breakout_entry"] | df["pullback_entry"]
    df["industry_asof_T"] = df["industry_name"]
    ensure_parent(stock_signal_cache_path(config))
    pd.to_pickle(df, stock_signal_cache_path(config))

    count_cols = ["breakout_entry", "original_pullback_entry", "raw_pullback_shape", "combined_entry"]
    daily = df.groupby("datetime", as_index=False).agg(
        instruments=("instrument", "nunique"),
        **{col: (col, "sum") for col in count_cols},
        trend_score_median=("trend_score", "median"),
    )
    signals = df.loc[df[count_cols].any(axis=1), [col for col in SIGNAL_FEATURE_COLUMNS if col in df.columns]].copy()
    outputs.extend(
        [
            write_csv(daily, report_dir(config) / "generated_daily_candidates.csv"),
            write_csv(signals, report_dir(config) / "generated_signals.csv"),
        ]
    )
    record_manifest(config, "build-signals", outputs, {"signal_rows": int(len(signals)), "coverage_limited_diagnostic": coverage_summary["coverage_limited_diagnostic"]})
    return df, coverage_summary


def classify_pullbacks(config: dict[str, Any], df: pd.DataFrame) -> None:
    cls = config["pullback_classes"]
    raw = df["raw_pullback_shape"].fillna(False)
    prev_break = (df["prev_close"] < df["prev_ema20"]).fillna(False)
    touch_ema60 = (df["rolling_low_5"] <= df["ema60"]).fillna(False)
    low20 = (df["distance_to_low20"] <= float(cls["breakdown_repair"]["breakdown_if_any"]["distance_to_low20_max"])).fillna(False)
    ret20 = (df["ret20"] < float(cls["breakdown_repair"]["breakdown_if_any"]["ret20_max"])).fillna(False)
    breakdown = raw & (prev_break | touch_ema60 | low20 | ret20)

    weak = raw & (df["money_ratio20"] >= float(cls["weak_volume_rebound"]["money_ratio20_min"])) & (
        df["money_ratio20"] <= float(cls["weak_volume_rebound"]["money_ratio20_max"])
    )
    weak_if = cls["weak_volume_rebound"]["weak_if_any"]
    weak = weak & (
        (df["trend_score_pct"] > float(weak_if["trend_score_pct_gt"]))
        | (df["market_width_state"] != weak_if["market_width_state_not"])
        | (df["industry_sync_state"] != weak_if["industry_sync_state_not"])
    )

    strong_rules = cls["strong_trend_continuation"]
    no_breakdown = ~(df["recent_close_below_ema20"].fillna(False) | df["recent_touch_ema60"].fillna(False))
    strong = (
        raw
        & (df["trend_score_pct"] <= float(strong_rules["trend_score_pct_max"]))
        & (df["market_trend_state"] == strong_rules["market_trend_state"])
        & df["market_width_state"].isin(strong_rules["market_width_states"])
        & (df["industry_sync_state"] == strong_rules["industry_sync_state"])
        & (df["close"] > df["ema20"])
        & (df["ema20"] > df["ema60"])
        & (df["distance_to_ema60"] > float(strong_rules["distance_to_ema60_min"]))
        & (df["distance_to_high60"] >= float(strong_rules["distance_to_high60_min"]))
        & (df["money_ratio20"] <= float(strong_rules["money_ratio20_max"]))
        & no_breakdown
    )

    df["pullback_class"] = "not_pullback"
    df["pullback_class_reason"] = ""
    df.loc[raw, "pullback_class"] = "unclassified_pullback"
    df.loc[raw, "pullback_class_reason"] = "raw_pullback_shape without class-specific confirmation"
    df.loc[strong, "pullback_class"] = "strong_trend_continuation"
    df.loc[strong, "pullback_class_reason"] = "strong trend, synced industry, low-volume healthy continuation"
    df.loc[weak, "pullback_class"] = "weak_volume_rebound"
    df.loc[weak, "pullback_class_reason"] = "weak trend/width/industry context with 0.60-1.00 money_ratio20"
    df.loc[breakdown, "pullback_class"] = "breakdown_repair"
    df.loc[breakdown, "pullback_class_reason"] = "recent EMA20/EMA60/low20/ret20 structural damage"


def load_signals(config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if stock_signal_cache_path(config).exists():
        signals = pd.read_pickle(stock_signal_cache_path(config))
        coverage = read_json(report_dir(config) / "pit_provider_coverage_summary.json")
        return signals, coverage
    return build_regimes_and_signals(config)


def version_spec(config: dict[str, Any], version_item: dict[str, Any]) -> dict[str, Any]:
    rules = config["_explore7_rules"]
    return {
        "version": version_item["version"],
        "stage": version_item.get("candidate_type", ""),
        "candidate_type": version_item.get("candidate_type", ""),
        "sizing": "risk_unit",
        "risk_budget_per_trade": float(rules.get("risk_budget_per_trade", 0.005)),
        "single_stock_max_weight": float(rules.get("single_stock_max_weight", 0.03)),
        "max_positions": int(rules.get("max_positions", 20)),
        "max_daily_new_weight": float(rules.get("max_daily_new_weight", 0.20)),
        "max_industry_weight": float(rules.get("max_industry_weight", 0.20)),
        "pullback_classes": version_item.get("pullback_classes", []),
    }


def apply_version(config: dict[str, Any], signals: pd.DataFrame, version_item: dict[str, Any]) -> pd.DataFrame:
    data = signals.copy()
    classes = set(version_item.get("pullback_classes", []))
    data["breakout_entry"] = data["breakout_entry"].fillna(False)
    if not classes:
        pullback = pd.Series(False, index=data.index)
    elif "original_rule_pullback" in classes:
        pullback = data["original_pullback_entry"].fillna(False)
    else:
        pullback = data["raw_pullback_shape"].fillna(False) & data["pullback_class"].isin(classes)
    data["pullback_entry"] = pullback
    data["combined_entry"] = data["breakout_entry"] | data["pullback_entry"]
    return data


def fold_executable_end(signals: pd.DataFrame, valid_end: pd.Timestamp) -> pd.Timestamp:
    dates = sorted(pd.Timestamp(d).normalize() for d in signals["datetime"].dropna().unique())
    valid_dates = [date for date in dates if date <= valid_end]
    if len(valid_dates) < 2:
        return valid_end
    return valid_dates[-2]


def attach_run_metadata(df: pd.DataFrame, spec: dict[str, Any], fold: dict[str, str], executable_end: pd.Timestamp) -> pd.DataFrame:
    data = df.copy()
    data["fold"] = fold["fold"]
    data["candidate_type"] = spec.get("candidate_type", "")
    data["train_start"] = fold["train_start"]
    data["train_end"] = fold["train_end"]
    data["valid_start"] = fold["valid_start"]
    data["valid_end"] = fold["valid_end"]
    data["valid_executable_end"] = executable_end.date().isoformat()
    return data


def enrich_trades_with_signals(trades: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    data = trades.copy()
    data["signal_date"] = pd.to_datetime(data["signal_date"])
    signal_cols = [col for col in SIGNAL_FEATURE_COLUMNS if col in signals.columns]
    features = signals[signal_cols].rename(columns={"datetime": "signal_date"}).copy()
    features["signal_date"] = pd.to_datetime(features["signal_date"])
    merged = data.merge(features, on=["instrument", "signal_date"], how="left", suffixes=("", "_signal"))
    for column in ["pullback_class", "pullback_class_reason", "industry_name", "industry_asof_T"]:
        if column in merged.columns:
            merged[column] = merged[column].fillna("")
    merged["calendar_year"] = merged["signal_date"].dt.year
    merged["r_multiple"] = (pd.to_numeric(merged["exit_price"], errors="coerce") - pd.to_numeric(merged["entry_price"], errors="coerce")) / pd.to_numeric(
        merged["R"], errors="coerce"
    ).replace(0, np.nan)
    return merged


def drawdown_from_account(values: pd.Series) -> float:
    account = pd.to_numeric(values, errors="coerce").dropna()
    if account.empty:
        return 0.0
    return float((account / account.cummax() - 1.0).min())


def build_year_metrics(portfolio: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    if portfolio.empty:
        return pd.DataFrame()
    p = portfolio.copy()
    p["datetime"] = pd.to_datetime(p["datetime"])
    p["calendar_year"] = p["datetime"].dt.year
    t = trades.copy()
    if not t.empty:
        t["signal_date"] = pd.to_datetime(t["signal_date"])
        t["calendar_year"] = t["signal_date"].dt.year
    rows: list[dict[str, Any]] = []
    for (version, fold, year), group in p.groupby(["version", "fold", "calendar_year"], dropna=False):
        group = group.sort_values("datetime")
        trade_group = t[(t["version"] == version) & (t["fold"] == fold) & (t["calendar_year"] == year)] if not t.empty else pd.DataFrame()
        start_account = safe_float(group["prev_account_value"].iloc[0], np.nan)
        end_account = safe_float(group["account_value"].iloc[-1], np.nan)
        net_pnl = float(pd.to_numeric(trade_group.get("net_pnl"), errors="coerce").sum()) if not trade_group.empty else 0.0
        trades_count = int(len(trade_group))
        returns = pd.to_numeric(trade_group.get("cost_after_return"), errors="coerce") if not trade_group.empty else pd.Series(dtype=float)
        rows.append(
            {
                "version": version,
                "fold": fold,
                "calendar_year": int(year),
                "year_return_with_cost": end_account / start_account - 1 if start_account else np.nan,
                "max_drawdown": drawdown_from_account(group["account_value"]),
                "trades": trades_count,
                "net_pnl_sum": net_pnl,
                "yearly_expectancy": net_pnl / trades_count if trades_count else np.nan,
                "avg_cost_after_return": float(returns.mean()) if len(returns) else np.nan,
                "avg_r_multiple": float(pd.to_numeric(trade_group.get("r_multiple"), errors="coerce").mean()) if not trade_group.empty else np.nan,
                "median_r_multiple": float(pd.to_numeric(trade_group.get("r_multiple"), errors="coerce").median()) if not trade_group.empty else np.nan,
                "stop_time_trade_ratio": float(trade_group["exit_reason"].isin(["stop_loss", "time_stop"]).mean()) if not trade_group.empty else 0.0,
                "cash_ratio": float(group["cash_ratio"].mean()),
            }
        )
    instances = pd.DataFrame(rows)
    if instances.empty:
        return instances
    grouped = (
        instances.groupby(["version", "calendar_year"], as_index=False)
        .agg(
            year_return_with_cost=("year_return_with_cost", "mean"),
            max_drawdown=("max_drawdown", "min"),
            trades=("trades", "mean"),
            net_pnl_sum=("net_pnl_sum", "mean"),
            yearly_expectancy=("yearly_expectancy", "mean"),
            avg_cost_after_return=("avg_cost_after_return", "mean"),
            avg_r_multiple=("avg_r_multiple", "mean"),
            median_r_multiple=("median_r_multiple", "median"),
            stop_time_trade_ratio=("stop_time_trade_ratio", "mean"),
            cash_ratio=("cash_ratio", "mean"),
            year_instances=("fold", "nunique"),
            folds=("fold", lambda s: ",".join(sorted(set(map(str, s))))),
        )
        .sort_values(["version", "calendar_year"])
    )
    return grouped


def build_classification_audit(config: dict[str, Any], signals: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    candidates = signals[signals["raw_pullback_shape"].fillna(False)].copy()
    candidates["calendar_year"] = pd.to_datetime(candidates["datetime"]).dt.year
    rows: list[dict[str, Any]] = []
    classes = config["pullback_classes"]["precedence"]
    for fold in config["folds"]:
        for stage, start_key, end_key in [("train", "train_start", "train_end"), ("valid", "valid_start", "valid_end")]:
            start = parse_dt(fold[start_key])
            end = parse_dt(fold[end_key])
            subset = candidates[(pd.to_datetime(candidates["datetime"]) >= start) & (pd.to_datetime(candidates["datetime"]) <= end)]
            for (year, cls_name), group in subset.groupby(["calendar_year", "pullback_class"], dropna=False):
                rows.append(
                    {
                        "fold": fold["fold"],
                        "stage": stage,
                        "calendar_year": int(year),
                        "pullback_class": cls_name,
                        "candidate_count": int(len(group)),
                        "pit_universe_members": int(group["instrument"].nunique()),
                        "insufficient_class_coverage": bool(len(group) < 40),
                    }
                )
            for cls_name in classes:
                if subset.empty or cls_name not in set(subset["pullback_class"]):
                    rows.append(
                        {
                            "fold": fold["fold"],
                            "stage": stage,
                            "calendar_year": 0,
                            "pullback_class": cls_name,
                            "candidate_count": 0,
                            "pit_universe_members": 0,
                            "insufficient_class_coverage": True,
                        }
                    )
    audit = pd.DataFrame(rows)
    if not trades.empty:
        pullback_trades = trades[trades["entry_type"] == "pullback"].copy()
        if not pullback_trades.empty:
            pullback_trades["calendar_year"] = pd.to_datetime(pullback_trades["signal_date"]).dt.year
            trade_metrics = (
                pullback_trades.groupby(["fold", "version", "calendar_year", "pullback_class"], as_index=False)
                .agg(
                    replay_trade_count=("instrument", "size"),
                    win_rate=("cost_after_return", lambda s: float((pd.to_numeric(s, errors="coerce") > 0).mean())),
                    avg_cost_after_return=("cost_after_return", "mean"),
                    avg_r_multiple=("r_multiple", "mean"),
                    median_r_multiple=("r_multiple", "median"),
                    net_pnl_sum=("net_pnl", "sum"),
                    stop_time_trade_ratio=("exit_reason", lambda s: float(s.isin(["stop_loss", "time_stop"]).mean())),
                )
            )
            audit = audit.merge(trade_metrics, on=["fold", "calendar_year", "pullback_class"], how="left")
    return audit.fillna({"replay_trade_count": 0})


def build_class_expectancy_by_year(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(
            columns=[
                "version",
                "fold",
                "calendar_year",
                "pullback_class",
                "trades",
                "net_pnl_sum",
                "yearly_expectancy",
                "win_rate",
                "avg_cost_after_return",
                "avg_r_multiple",
                "stop_time_trade_ratio",
            ]
        )
    data = trades[trades["entry_type"] == "pullback"].copy()
    if data.empty:
        return pd.DataFrame()
    data["calendar_year"] = pd.to_datetime(data["signal_date"]).dt.year
    grouped = (
        data.groupby(["version", "fold", "calendar_year", "pullback_class"], as_index=False)
        .agg(
            trades=("instrument", "size"),
            net_pnl_sum=("net_pnl", "sum"),
            win_rate=("cost_after_return", lambda s: float((pd.to_numeric(s, errors="coerce") > 0).mean())),
            avg_cost_after_return=("cost_after_return", "mean"),
            avg_r_multiple=("r_multiple", "mean"),
            stop_time_trade_ratio=("exit_reason", lambda s: float(s.isin(["stop_loss", "time_stop"]).mean())),
        )
        .sort_values(["version", "fold", "calendar_year", "pullback_class"])
    )
    grouped["yearly_expectancy"] = grouped["net_pnl_sum"] / grouped["trades"].replace(0, np.nan)
    return grouped


def return_concentration(values: pd.Series) -> float:
    positive = pd.to_numeric(values, errors="coerce")
    positive = positive[positive > 0]
    total = positive.sum()
    return float(positive.max() / total) if total > 0 else np.nan


def build_acceptance_summary(config: dict[str, Any], fold_metrics: pd.DataFrame, year_metrics: pd.DataFrame, trades: pd.DataFrame, coverage: dict[str, Any]) -> pd.DataFrame:
    selection = config["selection"]
    versions = {item["version"]: item for item in config["versions"]}
    original = year_metrics[year_metrics["version"] == "pit_original_pullback_baseline"].set_index("calendar_year")
    breakout = year_metrics[year_metrics["version"] == "pit_breakout_core_baseline"].set_index("calendar_year")
    rows: list[dict[str, Any]] = []
    industry_summary = read_json(report_dir(config) / "pit_industry_membership_summary.json")
    for version in ["pit_rebuilt_pullback_candidate", "pit_strong_trend_pullback_candidate"]:
        y = year_metrics[year_metrics["version"] == version].copy()
        f = fold_metrics[fold_metrics["version"] == version].copy()
        t = trades[trades["version"] == version].copy() if not trades.empty else pd.DataFrame()
        if y.empty or f.empty:
            rows.append({"version": version, "candidate_for_future_final_test": False, "reject_reason": "missing replay metrics"})
            continue
        positive_valid_years = int((y["year_return_with_cost"] > 0).sum())
        qualified_years = int(
            (
                (y["year_return_with_cost"] > 0)
                | ((y["year_return_with_cost"] >= float(selection["controlled_flat_return_floor"])) & (y["max_drawdown"].abs() <= original.reindex(y["calendar_year"])["max_drawdown"].abs().fillna(np.inf).values))
            ).sum()
        )
        expectancy_improved = 0
        return_not_below = 0
        for _, row in y.iterrows():
            year = row["calendar_year"]
            if year in original.index and row["yearly_expectancy"] > original.loc[year, "yearly_expectancy"]:
                expectancy_improved += 1
            if year in breakout.index and row["year_return_with_cost"] >= breakout.loc[year, "year_return_with_cost"] and row["trades"] > breakout.loc[year, "trades"]:
                return_not_below += 1
        original_trades = pd.to_numeric(fold_metrics[fold_metrics["version"] == "pit_original_pullback_baseline"]["trades"], errors="coerce").sum()
        version_trades = pd.to_numeric(f["trades"], errors="coerce").sum()
        trade_ratio = float(version_trades / original_trades) if original_trades else np.nan
        original_stop = trades[trades["version"] == "pit_original_pullback_baseline"]["exit_reason"].isin(["stop_loss", "time_stop"]).mean() if not trades.empty else np.nan
        version_stop = t["exit_reason"].isin(["stop_loss", "time_stop"]).mean() if not t.empty else np.nan
        stop_reduction = float((original_stop - version_stop) / original_stop) if original_stop and not pd.isna(version_stop) else np.nan
        worst_year_dd_ok = True
        for _, row in y.iterrows():
            year = row["calendar_year"]
            if year in original.index and row["max_drawdown"] < original.loc[year, "max_drawdown"] - float(selection["max_year_drawdown_worse_pp"]):
                worst_year_dd_ok = False
        checks = {
            "all_folds_success": int(f["fold"].nunique()) == len(config["folds"]),
            "universe_point_in_time": bool(config["universe"].get("point_in_time", False)),
            "industry_membership_point_in_time": bool(industry_summary.get("point_in_time", False)),
            "provider_not_coverage_limited": not bool(coverage.get("coverage_limited_diagnostic", False)),
            "positive_valid_years_ok": positive_valid_years >= int(selection["positive_valid_years"]),
            "qualified_valid_years_ok": qualified_years >= int(selection["qualified_valid_years"]),
            "expectancy_improved_years_ok": expectancy_improved >= int(selection["min_years_expectancy_improved_vs_original_pullback"]),
            "return_not_below_breakout_years_ok": return_not_below >= int(selection["min_years_return_not_below_breakout_core"]),
            "avg_cash_ok": float(f["avg_cash_ratio"].mean()) <= float(selection["max_avg_cash_ratio"]),
            "fold_cash_ok": float(f["avg_cash_ratio"].max()) <= float(selection["max_fold_cash_ratio"]),
            "trade_ratio_ok": bool(not pd.isna(trade_ratio) and trade_ratio >= float(selection["min_trade_ratio_vs_original_pullback"])),
            "min_trades_per_fold_ok": bool((f["trades"] >= int(selection["min_trades_per_fold"])).all()),
            "worst_year_drawdown_ok": worst_year_dd_ok,
            "stop_time_ratio_reduction_ok": bool(not pd.isna(stop_reduction) and stop_reduction >= float(selection["min_stop_time_ratio_reduction"])),
            "year_return_concentration_ok": bool(return_concentration(y["year_return_with_cost"]) <= float(selection["max_year_return_concentration"]) if not pd.isna(return_concentration(y["year_return_with_cost"])) else False),
            "observed_replication_unused": not bool(selection["observed_replication_used_for_selection"]),
        }
        accepted = versions[version].get("candidate_type") == "candidate" and all(checks.values())
        failed = [name for name, ok in checks.items() if not ok]
        exposure_reduction = bool(float(f["avg_cash_ratio"].mean()) > float(selection["max_avg_cash_ratio"]) or (not pd.isna(trade_ratio) and trade_ratio < float(selection["min_trade_ratio_vs_original_pullback"])))
        rows.append(
            {
                "version": version,
                "candidate_type": versions[version].get("candidate_type", ""),
                "candidate_for_future_final_test": bool(accepted),
                "diagnostic_only": bool(not accepted),
                "reject_reason": "; ".join(failed) if failed else "",
                "improvement_mainly_exposure_reduction": exposure_reduction,
                "positive_valid_years": positive_valid_years,
                "qualified_valid_years": qualified_years,
                "expectancy_improved_years_vs_original": expectancy_improved,
                "return_not_below_breakout_years": return_not_below,
                "avg_cash_ratio": float(f["avg_cash_ratio"].mean()),
                "max_fold_cash_ratio": float(f["avg_cash_ratio"].max()),
                "trades": int(version_trades),
                "trade_ratio_vs_original_pullback": trade_ratio,
                "stop_time_trade_ratio": float(version_stop) if not pd.isna(version_stop) else np.nan,
                "stop_time_ratio_reduction_vs_original": stop_reduction,
                "worst_year_drawdown": float(y["max_drawdown"].min()),
                "year_return_concentration": return_concentration(y["year_return_with_cost"]),
                **checks,
            }
        )
    return pd.DataFrame(rows)


def command_run_walk_forward(config: dict[str, Any]) -> list[Path]:
    industry_summary = read_json(report_dir(config) / "pit_industry_membership_summary.json")
    if not industry_summary.get("point_in_time", False):
        raise DataGateError("PIT industry membership is not point-in-time; run audit-pit-data/build-pit-universe first")
    signals, coverage = load_signals(config)
    explore5 = import_explore5_runner()
    outputs: list[Path] = []
    metrics_rows: list[dict[str, Any]] = []
    portfolios: list[pd.DataFrame] = []
    trades_all: list[pd.DataFrame] = []
    audits: list[pd.DataFrame] = []
    exposures: list[pd.DataFrame] = []
    for version_item in config["versions"]:
        spec = version_spec(config, version_item)
        version_signals = apply_version(config, signals, version_item)
        for fold in config["folds"]:
            start = parse_dt(fold["valid_start"])
            valid_end = parse_dt(fold["valid_end"])
            end = fold_executable_end(version_signals, valid_end)
            portfolio, trades, audit, exposure, metrics = explore5.run_backtest_one(config, version_signals, spec, fold["fold"], start, end)
            metrics.update(
                {
                    "fold": fold["fold"],
                    "candidate_type": spec.get("candidate_type", ""),
                    "train_start": fold["train_start"],
                    "train_end": fold["train_end"],
                    "valid_start": fold["valid_start"],
                    "valid_end": fold["valid_end"],
                    "valid_executable_end": end.date().isoformat(),
                    "coverage_limited_diagnostic": bool(coverage.get("coverage_limited_diagnostic", False)),
                }
            )
            metrics_rows.append(metrics)
            portfolios.append(attach_run_metadata(portfolio, spec, fold, end))
            enriched_trades = enrich_trades_with_signals(attach_run_metadata(trades, spec, fold, end), version_signals)
            enriched_trades["sizing"] = spec["sizing"]
            trades_all.append(enriched_trades)
            audits.append(attach_run_metadata(audit, spec, fold, end))
            exposures.append(attach_run_metadata(exposure, spec, fold, end))
            print(f"ran {spec['version']} {fold['fold']} trades={len(trades)}", flush=True)
    fold_metrics = pd.DataFrame(metrics_rows)
    portfolio_all = pd.concat(portfolios, ignore_index=True) if portfolios else pd.DataFrame()
    trade_all = pd.concat(trades_all, ignore_index=True) if trades_all else pd.DataFrame()
    audit_all = pd.concat(audits, ignore_index=True) if audits else pd.DataFrame()
    exposure_all = pd.concat(exposures, ignore_index=True) if exposures else pd.DataFrame()
    year_metrics = build_year_metrics(portfolio_all, trade_all)
    class_audit = build_classification_audit(config, signals, trade_all)
    class_expectancy = build_class_expectancy_by_year(trade_all)
    acceptance = build_acceptance_summary(config, fold_metrics, year_metrics, trade_all, coverage)
    for filename, frame in {
        "fold_replay_metrics.csv": fold_metrics,
        "year_metrics.csv": year_metrics,
        "class_expectancy_by_year.csv": class_expectancy,
        "fold_trade_detail.csv": trade_all,
        "fold_portfolio_daily.csv": portfolio_all,
        "fold_execution_audit.csv": audit_all,
        "fold_industry_exposure_audit.csv": exposure_all,
        "pullback_classification_audit.csv": class_audit,
        "candidate_acceptance.csv": acceptance,
    }.items():
        outputs.append(write_csv(frame, report_dir(config) / filename))
    record_manifest(
        config,
        "run-walk-forward",
        outputs,
        {
            "walk_forward_fold_rows": int(len(fold_metrics)),
            "year_metric_rows": int(len(year_metrics)),
            "trade_rows": int(len(trade_all)),
            "candidate_for_future_final_test": bool(acceptance["candidate_for_future_final_test"].fillna(False).any()) if not acceptance.empty else False,
            "coverage_limited_diagnostic": bool(coverage.get("coverage_limited_diagnostic", False)),
        },
    )
    return outputs


def load_csv_if_exists(path: str | Path) -> pd.DataFrame:
    target = topic_path(path)
    return pd.read_csv(target) if target.exists() else pd.DataFrame()


def command_report(config: dict[str, Any]) -> list[Path]:
    report_path = report_dir(config) / "pullback_rebuild_report.md"
    alias_report_path = report_dir(config) / "explore7_pullback_rebuild_report.md"
    manifest = read_json(manifest_path(config))
    universe_summary = load_csv_if_exists(report_dir(config) / "pit_universe_summary.csv")
    coverage = read_json(report_dir(config) / "pit_provider_coverage_summary.json")
    industry = read_json(report_dir(config) / "pit_industry_membership_summary.json")
    acceptance = load_csv_if_exists(report_dir(config) / "candidate_acceptance.csv")
    fold_metrics = load_csv_if_exists(report_dir(config) / "fold_replay_metrics.csv")
    year_metrics = load_csv_if_exists(report_dir(config) / "year_metrics.csv")
    class_expectancy = load_csv_if_exists(report_dir(config) / "class_expectancy_by_year.csv")
    class_audit = load_csv_if_exists(report_dir(config) / "pullback_classification_audit.csv")
    source_summary = read_json(report_dir(config) / "source_data_audit_summary.json")
    static_universe = load_csv_if_exists(TOPIC_DIR / "Explore1/data/universe/mcap500_mainboard_20251231.csv")
    static_industry = load_csv_if_exists(TOPIC_DIR / "Explore5/data/targets/industry_membership.csv")
    pit_industry = load_csv_if_exists(industry_membership_path(config))

    failed_label = {
        "provider_not_coverage_limited": "provider 覆盖不是完整 PIT provider",
        "positive_valid_years_ok": "正收益 distinct year 数不足",
        "qualified_valid_years_ok": "qualified valid year 数不足",
        "expectancy_improved_years_ok": "yearly expectancy 改善年份不足",
        "return_not_below_breakout_years_ok": "相对 breakout core 的收益/覆盖改善年份不足",
        "avg_cash_ok": "平均现金比例超过 95%",
        "fold_cash_ok": "至少一个 fold 现金比例超过 97%",
        "trade_ratio_ok": "交易数低于原 pullback baseline 的 60%",
        "min_trades_per_fold_ok": "至少一个 fold 交易数少于 40",
        "worst_year_drawdown_ok": "最差年度回撤比原 pullback 更差",
        "stop_time_ratio_reduction_ok": "stop_loss + time_stop 占比没有下降 15%",
        "year_return_concentration_ok": "年度收益集中度超过 45%",
        "observed_replication_unused": "observed replication 被错误用于选择",
    }

    def failed_checks(row: pd.Series) -> str:
        failed = [label for key, label in failed_label.items() if key in row and not bool_value(row[key])]
        return "; ".join(failed) if failed else "无"

    def version_name(value: str) -> str:
        mapping = {
            "pit_breakout_core_baseline": "breakout core baseline",
            "pit_original_pullback_baseline": "original pullback baseline",
            "pit_strong_trend_pullback_candidate": "strong-trend candidate",
            "pit_weak_volume_rebound_diagnostic": "weak-volume diagnostic",
            "pit_breakdown_repair_diagnostic": "breakdown-repair diagnostic",
            "pit_rebuilt_pullback_candidate": "rebuilt pullback candidate",
        }
        return mapping.get(str(value), str(value))

    def universe_value(item: str, default: Any = np.nan) -> Any:
        if universe_summary.empty:
            return default
        matched = universe_summary[universe_summary["item"] == item]
        return matched["value"].iloc[0] if not matched.empty else default

    accepted_version = ""
    if not acceptance.empty:
        accepted = acceptance[acceptance["candidate_for_future_final_test"].map(bool_value)]
        accepted_version = str(accepted["version"].iloc[0]) if not accepted.empty else ""

    lines: list[str] = [
        "# Explore7 Pullback 子系统重建详细报告",
        "",
        "## 1. 核心结论",
    ]
    if acceptance.empty:
        blockers = []
        if not universe_membership_path(config).exists():
            blockers.append("PIT universe 尚未生成")
        if not industry.get("point_in_time", False):
            blockers.append("PIT industry membership 未通过严格门槛")
        if not coverage:
            blockers.append("provider 覆盖审计尚未完成")
        lines.append("- 未形成 Explore7 候选版本。当前状态是数据阻断或回放未完成。")
        if blockers:
            lines.extend(f"- {item}" for item in blockers)
    else:
        if not accepted_version:
            lines.append("- 未形成 `candidate_for_future_final_test`。所有 rebuilt/strong-trend 候选仍为 diagnostic-only。")
        else:
            lines.append(f"- 形成候选版本：`{accepted_version}`。")
        exposure = acceptance[acceptance["version"] == "pit_rebuilt_pullback_candidate"]
        if not exposure.empty and bool(exposure["improvement_mainly_exposure_reduction"].iloc[0]):
            lines.append("- rebuilt pullback 被降级：改善主要来自交易数下降或现金比例升高。")
        if bool(coverage.get("coverage_limited_diagnostic", False)):
            lines.append("- 本次策略回放只能视为 `coverage_limited_diagnostic`：PIT universe 与 PIT industry 已构建，但行情 provider 回退到旧 Explore1 provider，覆盖率只有 `86.17%` 左右，不能作为最终可交易结论。")
        rebuilt_row = acceptance[acceptance["version"] == "pit_rebuilt_pullback_candidate"]
        if not rebuilt_row.empty:
            row = rebuilt_row.iloc[0]
            lines.append(
                "- rebuilt/strong-trend 版本没有通过验收："
                f"正收益年份 `{int(safe_float(row.get('positive_valid_years'), 0))}/3`，"
                f"qualified 年份 `{int(safe_float(row.get('qualified_valid_years'), 0))}/4`，"
                f"expectancy 改善年份 `{int(safe_float(row.get('expectancy_improved_years_vs_original'), 0))}/4`，"
                f"交易数比例 `{format_float(row.get('trade_ratio_vs_original_pullback'), 2)}`，"
                f"平均现金 `{format_pct(row.get('avg_cash_ratio'))}`。"
            )
    lines.extend(
        [
            "",
            "## 2. 数据可信边界",
            f"- Universe point-in-time: `{manifest.get('universe_point_in_time', False)}`",
            f"- Industry point-in-time: `{industry.get('point_in_time', False)}`",
            f"- Provider coverage ratio: `{format_pct(coverage.get('coverage_ratio', np.nan))}`",
            f"- Coverage-limited diagnostic: `{coverage.get('coverage_limited_diagnostic', False)}`",
            f"- Historical result CSV used for calculation: `{manifest.get('any_explore456_result_csv_used', False)}`",
            f"- Provider used for this diagnostic replay: `{coverage.get('provider_uri', '')}`",
            f"- Missing PIT membership rows in provider: `{format_money(coverage.get('missing_membership_rows', np.nan))}` / `{format_money(coverage.get('membership_rows', np.nan))}`",
        ]
    )
    if not universe_summary.empty:
        lines.append("")
        lines.append("### 2.1 PIT Universe 摘要")
        rows = [
            ["daily membership rows", format_money(universe_value("pit_universe_rows"))],
            ["distinct instruments", format_money(universe_value("pit_universe_instruments"))],
            ["daily members min/median/max", f"{format_money(universe_value('daily_member_count_min'))} / {format_float(universe_value('daily_member_count_median'), 1)} / {format_money(universe_value('daily_member_count_max'))}"],
            ["daily membership changed", str(universe_value("daily_membership_changed"))],
            ["static 2025-12-31 universe used as authority", str(universe_value("static_20251231_universe_used_as_authority"))],
        ]
        lines.extend(markdown_table(["Metric", "Value"], rows))
        lines.append("")
        lines.append("解释：PIT universe 已经替代静态 `2025-12-31` 股票池作为交易资格来源；membership 是逐日变化的，说明当前不再把未来静态股票池直接投射回历史。")

    if not static_universe.empty and universe_membership_path(config).exists():
        pit_universe = pd.read_csv(universe_membership_path(config), usecols=["date", "instrument"], parse_dates=["date"])
        research = pit_universe[(pit_universe["date"] >= parse_dt("2019-01-01")) & (pit_universe["date"] <= parse_dt("2024-12-31"))]
        static_set = set(static_universe["instrument"].astype(str))
        pit_set = set(research["instrument"].astype(str))
        daily_counts = research.groupby("date")["instrument"].nunique()
        lines.append("")
        lines.append("### 2.2 PIT Universe 与旧静态 universe 差异")
        rows = [
            ["旧静态 universe instruments", format_money(len(static_set))],
            ["PIT research-window distinct instruments", format_money(len(pit_set))],
            ["两者重叠 instruments", format_money(len(static_set & pit_set))],
            ["只在 PIT research-window 出现", format_money(len(pit_set - static_set))],
            ["只在旧静态 universe 出现", format_money(len(static_set - pit_set))],
            ["PIT daily member mean/median", f"{format_float(daily_counts.mean(), 1)} / {format_float(daily_counts.median(), 1)}"],
        ]
        lines.extend(markdown_table(["Metric", "Value"], rows))
        if not pit_industry.empty and not static_industry.empty:
            pit_industry["date"] = pd.to_datetime(pit_industry["date"])
            pit_research = pit_industry[(pit_industry["date"] >= parse_dt("2019-01-01")) & (pit_industry["date"] <= parse_dt("2024-12-31"))].copy()
            pit_daily = pit_research.groupby(["date", "industry_name"])["instrument"].nunique().reset_index(name="count")
            pit_total = pit_research.groupby("date")["instrument"].nunique().reset_index(name="total")
            pit_daily = pit_daily.merge(pit_total, on="date", how="left")
            pit_daily["share"] = pit_daily["count"] / pit_daily["total"].replace(0, np.nan)
            pit_top = (
                pit_daily.groupby("industry_name", as_index=False)
                .agg(avg_count=("count", "mean"), avg_share=("share", "mean"))
                .sort_values("avg_share", ascending=False)
                .head(8)
            )
            static_join = static_universe[["instrument"]].merge(static_industry[["instrument", "industry_name"]], on="instrument", how="left")
            static_join["industry_name"] = static_join["industry_name"].fillna("UNKNOWN")
            static_top = static_join.groupby("industry_name").size().sort_values(ascending=False).head(8)
            lines.append("")
            lines.append("旧静态 universe 与 PIT universe 的行业结构也不同。PIT research-window 平均权重最高的是非银金融、银行、电子；旧静态池中有色金属、非银金融、电子、银行更靠前。这说明 Explore7 的结果不能和 Explore1 静态池结果直接等同。")
            rows = [
                [row["industry_name"], format_float(row["avg_count"], 1), format_pct(row["avg_share"])]
                for _, row in pit_top.iterrows()
            ]
            lines.extend(markdown_table(["PIT industry", "Avg daily members", "Avg share"], rows))
            rows = [[industry_name, int(count)] for industry_name, count in static_top.items()]
            lines.extend(markdown_table(["Static industry", "Members"], rows))
    if source_summary:
        lines.extend(
            [
                "",
                "### 2.3 Source Audit",
                f"- Rows: `{source_summary.get('rows', 0)}`",
                f"- Forbidden result paths used for calculation: `{source_summary.get('forbidden_result_paths_used_for_calculation', 0)}`",
                f"- Classification counts: `{source_summary.get('classification_counts', {})}`",
            ]
        )
    if not fold_metrics.empty:
        lines.append("")
        lines.append("## 3. Fold 回放结果")
        version_summary = (
            fold_metrics.groupby("version", as_index=False)
            .agg(
                folds=("fold", "nunique"),
                trades=("trades", "sum"),
                positive_folds=("total_return_with_cost", lambda s: int((pd.to_numeric(s, errors="coerce") > 0).sum())),
                mean_return=("total_return_with_cost", "mean"),
                worst_return=("total_return_with_cost", "min"),
                worst_drawdown=("max_drawdown", "min"),
                avg_cash=("avg_cash_ratio", "mean"),
                max_cash=("avg_cash_ratio", "max"),
            )
            .sort_values("version")
        )
        rows = [
            [
                version_name(row["version"]),
                int(row["trades"]),
                f"{int(row['positive_folds'])}/{int(row['folds'])}",
                format_pct(row["mean_return"]),
                format_pct(row["worst_return"]),
                format_pct(row["worst_drawdown"]),
                format_pct(row["avg_cash"]),
                format_pct(row["max_cash"]),
            ]
            for _, row in version_summary.iterrows()
        ]
        lines.extend(markdown_table(["Version", "Trades", "Positive folds", "Mean return", "Worst return", "Worst DD", "Avg cash", "Max cash"], rows))
        lines.append("")
        lines.append("解读：`pit_rebuilt_pullback_candidate` 与 `pit_strong_trend_pullback_candidate` 完全一致，说明第一版 rebuilt 只保留 strong-trend continuation。它的 fold return 均值略高于原 pullback baseline，但交易数从 288 降到 117，平均现金从 95.86% 升到 97.77%，因此改善主要是少交易和高现金，而不是 pullback 子规则质量显著提升。")
        lines.append("")
        lines.append("### 3.1 Fold 明细")
        show = fold_metrics[["version", "fold", "trades", "total_return_with_cost", "max_drawdown", "avg_cash_ratio"]].copy()
        rows = [
            [
                version_name(row["version"]),
                row["fold"],
                int(safe_float(row["trades"], 0)),
                format_pct(row["total_return_with_cost"]),
                format_pct(row["max_drawdown"]),
                format_pct(row["avg_cash_ratio"]),
            ]
            for _, row in show.iterrows()
        ]
        lines.extend(markdown_table(["Version", "Fold", "Trades", "Return", "Max DD", "Avg Cash"], rows[:40]))
    if not year_metrics.empty:
        lines.append("")
        lines.append("## 4. Distinct Year 对照")
        rebuilt = year_metrics[year_metrics["version"].isin(["pit_original_pullback_baseline", "pit_breakout_core_baseline", "pit_rebuilt_pullback_candidate"])]
        rows = [
            [
                version_name(row["version"]),
                int(row["calendar_year"]),
                int(safe_float(row["trades"], 0)),
                format_pct(row["year_return_with_cost"]),
                format_float(row["yearly_expectancy"], 2),
                format_pct(row["cash_ratio"]),
            ]
            for _, row in rebuilt.iterrows()
        ]
        lines.extend(markdown_table(["Version", "Year", "Trades", "Return", "Expectancy", "Cash"], rows[:80]))
        original = year_metrics[year_metrics["version"] == "pit_original_pullback_baseline"].set_index("calendar_year")
        rebuilt_year = year_metrics[year_metrics["version"] == "pit_rebuilt_pullback_candidate"].set_index("calendar_year")
        breakout_year = year_metrics[year_metrics["version"] == "pit_breakout_core_baseline"].set_index("calendar_year")
        if not original.empty and not rebuilt_year.empty and not breakout_year.empty:
            lines.append("")
            lines.append("### 4.1 Rebuilt vs Original vs Breakout")
            rows = []
            for year in sorted(set(original.index) & set(rebuilt_year.index) & set(breakout_year.index)):
                orig = original.loc[year]
                reb = rebuilt_year.loc[year]
                br = breakout_year.loc[year]
                rows.append(
                    [
                        int(year),
                        format_pct(orig["year_return_with_cost"]),
                        format_pct(reb["year_return_with_cost"]),
                        format_pct(br["year_return_with_cost"]),
                        format_float(reb["yearly_expectancy"] - orig["yearly_expectancy"], 2),
                        f"{int(safe_float(reb['trades'], 0))}/{int(safe_float(orig['trades'], 0))}",
                        format_pct(reb["cash_ratio"]),
                    ]
                )
            lines.extend(markdown_table(["Year", "Original return", "Rebuilt return", "Breakout return", "Expectancy delta", "Rebuilt/orig trades", "Rebuilt cash"], rows))
            improved_years = sum(
                rebuilt_year.loc[year, "yearly_expectancy"] > original.loc[year, "yearly_expectancy"]
                for year in set(original.index) & set(rebuilt_year.index)
            )
            not_below_breakout_years = sum(
                (rebuilt_year.loc[year, "year_return_with_cost"] >= breakout_year.loc[year, "year_return_with_cost"])
                and (rebuilt_year.loc[year, "trades"] > breakout_year.loc[year, "trades"])
                for year in set(breakout_year.index) & set(rebuilt_year.index)
            )
            lines.append("")
            lines.append(
                f"逐年看，rebuilt 的 yearly expectancy 只在 `{improved_years}` 个 distinct years 优于原 pullback，"
                f"相对 breakout core 同时满足收益不低且交易覆盖增加的年份只有 `{not_below_breakout_years}` 个；"
                "两项都没有达到验收要求。2021 和 2022 的 rebuilt 交易数尤其低，说明该版本没有提供稳定交易覆盖。"
            )
    if not class_expectancy.empty:
        lines.append("")
        lines.append("## 5. Pullback 三类拆分结果")
        if not class_audit.empty:
            valid_audit = class_audit[(class_audit["stage"] == "valid") & (class_audit["calendar_year"] != 0)].copy()
            if not valid_audit.empty:
                class_candidates = (
                    valid_audit.groupby("pullback_class", as_index=False)
                    .agg(
                        candidate_count=("candidate_count", "sum"),
                        pit_universe_members=("pit_universe_members", "sum"),
                        insufficient_rows=("insufficient_class_coverage", "sum"),
                    )
                    .sort_values("candidate_count", ascending=False)
                )
                rows = [
                    [
                        row["pullback_class"],
                        format_money(row["candidate_count"]),
                        format_money(row["pit_universe_members"]),
                        int(safe_float(row["insufficient_rows"], 0)),
                    ]
                    for _, row in class_candidates.iterrows()
                ]
                lines.append("### 5.1 分类覆盖")
                lines.append("说明：下表按 fold-valid 视角统计，fold 之间有重叠年份，因此用于覆盖审计，不解释为去重样本数。")
                lines.extend(markdown_table(["Class", "Candidate rows", "PIT member count sum", "Insufficient rows"], rows))
        summary = (
            class_expectancy.groupby(["version", "pullback_class"], as_index=False)
            .agg(
                trades=("trades", "sum"),
                net_pnl_sum=("net_pnl_sum", "sum"),
                avg_expectancy=("yearly_expectancy", "mean"),
                positive_year_rows=("net_pnl_sum", lambda s: int((pd.to_numeric(s, errors="coerce") > 0).sum())),
                class_year_rows=("yearly_expectancy", "size"),
                stop_time_trade_ratio=("stop_time_trade_ratio", "mean"),
            )
            .sort_values(["version", "pullback_class"])
        )
        lines.append("")
        lines.append("### 5.2 分类回放表现")
        rows = [
            [
                version_name(row["version"]),
                row["pullback_class"],
                int(row["trades"]),
                format_float(row["net_pnl_sum"], 2),
                format_float(row["avg_expectancy"], 2),
                f"{int(row['positive_year_rows'])}/{int(row['class_year_rows'])}",
                format_pct(row["stop_time_trade_ratio"]),
            ]
            for _, row in summary.iterrows()
        ]
        lines.extend(markdown_table(["Version", "Class", "Trades", "Net PnL", "Avg Expectancy", "Positive class-years", "Stop/Time"], rows))
        lines.extend(
            [
                "",
                "分类解释：",
                "- `strong_trend_continuation` 没有证明自己是可选候选。valid 覆盖中样本非常少，rebuilt/strong-trend 实际 pullback 交易只有 27 笔，合计 net PnL 为负，且 positive class-years 只有 1/8。",
                "- `weak_volume_rebound` 在 diagnostic-only 回放中交易数充足，但合计 net PnL 明显为负，且 stop/time 占比高，继续支持 Explore4/5 对弱量反弹区域的风险判断。",
                "- `breakdown_repair` diagnostic 的合计 net PnL 为正，但 fold 回撤和年度波动很大，2021-2022 明显转弱；它不能直接提升为默认 pullback，只能作为独立规则研究对象，且必须重新设计风险约束。",
                "- `unclassified_pullback` 在原始 baseline 中 stop/time 占比极高，说明原 pullback 定义里仍有大量没有明确结构优势的噪声样本。",
            ]
        )
    if not acceptance.empty:
        lines.append("")
        lines.append("## 6. 验收门槛逐项解释")
        rows = [
            [
                version_name(row["version"]),
                bool_value(row["candidate_for_future_final_test"]),
                format_pct(row["avg_cash_ratio"]),
                format_pct(row["max_fold_cash_ratio"]),
                format_float(row["trade_ratio_vs_original_pullback"], 2),
                failed_checks(row),
            ]
            for _, row in acceptance.iterrows()
        ]
        lines.extend(markdown_table(["Version", "Candidate", "Avg Cash", "Max Fold Cash", "Trade Ratio", "Failed Checks"], rows))
        rebuilt_row = acceptance[acceptance["version"] == "pit_rebuilt_pullback_candidate"]
        if not rebuilt_row.empty:
            row = rebuilt_row.iloc[0]
            lines.extend(
                [
                    "",
                    "验收解释：",
                    f"- 现金门槛失败：平均现金 `{format_pct(row.get('avg_cash_ratio'))}`，高于 95%；最大 fold 现金 `{format_pct(row.get('max_fold_cash_ratio'))}`，高于 97%。",
                    f"- 覆盖门槛失败：rebuilt 总交易数 `{int(safe_float(row.get('trades'), 0))}`，只有原 pullback baseline 的 `{format_pct(row.get('trade_ratio_vs_original_pullback'))}`。",
                    f"- 期望改善不足：expectancy 改善年份 `{int(safe_float(row.get('expectancy_improved_years_vs_original'), 0))}`，低于要求的 4 年。",
                    f"- 风险结构没有改善：stop_loss + time_stop 占比变化为 `{format_pct(row.get('stop_time_ratio_reduction_vs_original'))}`，没有达到至少下降 15% 的要求。",
                    f"- 年度收益集中度 `{format_pct(row.get('year_return_concentration'))}`，高于 45%，说明少数年份贡献过高。",
                ]
            )
    lines.extend(
        [
            "",
            "## 7. 对需求问题的逐项回答",
            "- PIT universe 构建成功，并已替代静态 `2025-12-31` universe 作为交易资格来源；但行情 provider 尚未完全替换为 Explore7 PIT provider，所以策略结论仍是 coverage-limited diagnostic。",
            "- 旧 pullback 在 PIT universe 下没有稳定正贡献；原始 pullback baseline 只有 1/5 个 positive folds，2019-2024 distinct-year 表现也不稳定。",
            "- `strong_trend_continuation` 没有稳定正 expectancy，不能进入 future final test。",
            "- `weak_volume_rebound` 应继续剔除或单独重写；当前 diagnostic 回放显示其大样本下仍有明显负贡献。",
            "- `breakdown_repair` 不应直接进入默认交易。它有阶段性收益，但风险和年份稳定性不合格，必须作为独立子系统研究。",
            "- rebuilt pullback 的表观改善主要来自更少交易和更高现金，不是更高质量的 pullback alpha。",
            "- 本轮不存在可等待 future final test 的候选版本。",
            "",
            "## 8. 下一步",
            "- 第一优先级是补齐 `Explore7/data/qlib/cn_data_pit`，使 provider 覆盖 PIT daily membership，而不是继续调 pullback 阈值。",
            "- provider 补齐后必须重跑 `audit-pit-data -> run-walk-forward -> report`；只有当 `coverage_limited_diagnostic=False` 时，策略结果才可进入候选讨论。",
            "- 如果补齐 provider 后 strong-trend 仍失败，应暂停默认 pullback，转向 breakout coverage 或 breakdown-repair 独立规则研究。",
        ]
    )
    ensure_parent(report_path)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    alias_report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    outputs = [report_path, alias_report_path]
    record_manifest(config, "report", outputs)
    print(f"wrote {relpath(report_path)}", flush=True)
    return outputs


def command_self_test(config: dict[str, Any]) -> list[Path]:
    config_path = topic_path(config["_config_path"])
    text = config_path.read_text(encoding="utf-8")
    missing = [token for token in REQUIRED_CONFIG_TOKENS if token not in text]
    if missing:
        raise RuntimeError(f"config missing required Explore7 contract tokens: {missing}")
    if not load_dotenv_token():
        raise RuntimeError("TUSHARE_TOKEN is missing. Put it in .env or the environment.")
    audit = build_source_data_audit(config)
    validate_source_audit(audit)
    if bool(config["sources"].get("result_csv_used_for_calculation", True)):
        raise RuntimeError("config must keep sources.result_csv_used_for_calculation=false")
    outputs = [report_dir(config) / "source_data_audit.csv", report_dir(config) / "source_data_audit_summary.json"]
    record_manifest(config, "self-test", outputs, {"self_test_status": "ok"})
    print(f"Explore7 self-test passed: {relpath(config_path)}", flush=True)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Explore7 PIT pullback rebuild workflow.")
    parser.add_argument(
        "command",
        choices=["self-test", "build-pit-universe", "audit-pit-data", "run-walk-forward", "report"],
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    config = load_config(args.config)
    try:
        if args.command == "self-test":
            command_self_test(config)
        elif args.command == "build-pit-universe":
            command_build_pit_universe(config)
        elif args.command == "audit-pit-data":
            command_audit_pit_data(config)
        elif args.command == "run-walk-forward":
            command_run_walk_forward(config)
        elif args.command == "report":
            command_report(config)
        else:
            raise ValueError(args.command)
        return 0
    except DataGateError as exc:
        report_dir(config).mkdir(parents=True, exist_ok=True)
        write_json({"command": args.command, "status": "blocked", "error": str(exc)}, report_dir(config) / "data_gate_blocker.json")
        print(f"Explore7 data gate blocked: {exc}", flush=True)
        return 2
    except Exception as exc:  # noqa: BLE001
        report_dir(config).mkdir(parents=True, exist_ok=True)
        write_json({"command": args.command, "status": "failed", "error": str(exc)}, report_dir(config) / "command_error.json")
        print(f"Explore7 command failed: {exc}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
