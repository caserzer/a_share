#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import signal
import shutil
import sys
import traceback
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from dotenv import load_dotenv


EXPLORE_DIR = Path(__file__).resolve().parents[1]
TOPIC_DIR = EXPLORE_DIR.parent
FIELD_RENAME = {
    "$open": "open",
    "$high": "high",
    "$low": "low",
    "$close": "close",
    "$volume": "volume",
    "$money": "money",
    "$factor": "factor",
}
REPORT_COLUMNS = [
    "instrument",
    "signal_date",
    "order_date",
    "deal_date",
    "entry_type",
    "entry_price",
    "exit_signal_date",
    "exit_date",
    "exit_price",
    "initial_stop",
    "current_stop",
    "R",
    "exit_reason",
    "holding_days",
    "cost_before_return",
    "cost_after_return",
]


class ApiTimeoutError(TimeoutError):
    pass


@contextmanager
def api_timeout(seconds: int, label: str):
    def _handle_timeout(_signum, _frame):
        raise ApiTimeoutError(f"{label} timed out after {seconds}s")

    old_handler = signal.signal(signal.SIGALRM, _handle_timeout)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else TOPIC_DIR / path


def relpath(path: str | Path) -> str:
    path = Path(path).resolve()
    try:
        return str(path.relative_to(TOPIC_DIR))
    except ValueError:
        return str(path)


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = topic_path(path)
    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}
    config["_config_path"] = str(config_path)
    config["_config_hash"] = file_sha256(config_path)
    return config


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(df: pd.DataFrame, path: str | Path, **kwargs) -> Path:
    output = ensure_parent(topic_path(path))
    df.to_csv(output, index=False, **kwargs)
    return output


def write_json(data: dict[str, Any], path: str | Path) -> Path:
    output = ensure_parent(topic_path(path))
    with output.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
    return output


def read_json(path: str | Path) -> dict[str, Any]:
    target = topic_path(path)
    if not target.exists():
        return {}
    with target.open("r", encoding="utf-8") as file:
        return json.load(file)


def report_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["report_dir"])


def cache_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["cache_dir"])


def target_dir(config: dict[str, Any]) -> Path:
    return topic_path(config["paths"]["target_dir"])


def manifest_path(config: dict[str, Any]) -> Path:
    return report_dir(config) / "run_manifest.json"


def record_manifest(
    config: dict[str, Any],
    command: str,
    outputs: list[str | Path],
    extra: dict[str, Any] | None = None,
) -> None:
    path = manifest_path(config)
    manifest = read_json(path)
    load_dotenv(TOPIC_DIR / ".env", override=False)
    command_log = list(manifest.get("command_sequence", []))
    command_log.append(command)
    output_paths = sorted(set(manifest.get("output_paths", []) + [relpath(p) for p in outputs]))
    manifest.update(
        {
            "experiment": "Explore3 EMA trend rule strategy",
            "config_path": relpath(config["_config_path"]),
            "config_sha256": config["_config_hash"],
            "provider_uri": config["paths"]["provider_uri"],
            "stock_data_source": config["paths"]["provider_uri"],
            "market": config["qlib"]["market"],
            "benchmark": config["qlib"]["benchmark"],
            "tushare_token_present": bool(os.getenv("TUSHARE_TOKEN")),
            "command_sequence": command_log,
            "output_paths": output_paths,
            "risk_unit_sizing_enabled": bool(
                config["rules"]["portfolio"].get("risk_unit_sizing_enabled", False)
            ),
        }
    )
    if extra:
        manifest.update(extra)
    write_json(manifest, path)


def date_token(value: str) -> str:
    return str(value).replace("-", "")


def parse_dt(value: str | pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(value).normalize()


def ts_code_to_instrument(ts_code: str) -> str:
    text = str(ts_code).strip().upper()
    if "." in text:
        code, exchange = text.split(".", 1)
        prefix = {"SH": "SH", "SZ": "SZ", "BJ": "BJ"}.get(exchange, exchange[:2])
        return f"{prefix}{code.zfill(6)}"
    digits = "".join(ch for ch in text if ch.isdigit()).zfill(6)
    prefix = "SH" if digits.startswith("6") else "SZ"
    return f"{prefix}{digits}"


def instrument_to_ts_code(instrument: str) -> str:
    text = str(instrument).strip().upper()
    if "." in text:
        return text
    return f"{text[2:]}.{text[:2]}"


def target_records(config: dict[str, Any], target_type: str) -> pd.DataFrame:
    rows = []
    for record in config["targets"][target_type]:
        row = dict(record)
        row["target_type"] = target_type
        rows.append(row)
    return pd.DataFrame(rows)


def write_target_definitions(config: dict[str, Any]) -> list[Path]:
    outputs = []
    for target_type in ["market", "industry", "theme"]:
        path = target_dir(config) / f"{target_type}_targets.csv"
        outputs.append(write_csv(target_records(config, target_type), path))
    return outputs


def load_tushare_client(required: bool = False):
    load_dotenv(TOPIC_DIR / ".env", override=False)
    token = os.getenv("TUSHARE_TOKEN")
    if not token:
        if required:
            raise RuntimeError("TUSHARE_TOKEN is missing. Put it in .env or the environment.")
        return None
    import tushare as ts

    return ts.pro_api(token)


def normalize_index_history(
    df: pd.DataFrame,
    *,
    target: dict[str, Any],
    target_type: str,
    source: str,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    data = df.copy()
    rename = {
        "trade_date": "date",
        "日期": "date",
        "open": "open",
        "开盘": "open",
        "high": "high",
        "最高": "high",
        "low": "low",
        "最低": "low",
        "close": "close",
        "收盘": "close",
        "vol": "volume",
        "volume": "volume",
        "成交量": "volume",
        "amount": "money",
        "money": "money",
        "成交额": "money",
    }
    data = data.rename(columns={col: rename[col] for col in data.columns if col in rename})
    required = ["date", "open", "high", "low", "close"]
    if any(col not in data.columns for col in required):
        missing = [col for col in required if col not in data.columns]
        raise ValueError(f"{target['target_key']} missing fields after normalize: {missing}")
    data["date"] = pd.to_datetime(data["date"].astype(str), errors="coerce")
    for col in ["open", "high", "low", "close", "volume", "money"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")
        else:
            data[col] = np.nan
    data = data.dropna(subset=["date", "close"]).sort_values("date")
    data = data.drop_duplicates("date", keep="last")
    data["target_type"] = target_type
    data["target_key"] = target["target_key"]
    data["target_name"] = target["name"]
    data["ts_code"] = target.get("ts_code", "")
    data["source"] = source
    return data[
        [
            "target_type",
            "target_key",
            "target_name",
            "ts_code",
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "money",
            "source",
        ]
    ]


def fetch_tushare_history(
    pro,
    target: dict[str, Any],
    target_type: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    ts_start = date_token(start_date)
    ts_end = date_token(end_date)
    if target_type == "industry":
        with api_timeout(45, f"tushare.sw_daily {target['ts_code']}"):
            df = pro.sw_daily(ts_code=target["ts_code"], start_date=ts_start, end_date=ts_end)
        source = "tushare.sw_daily"
    else:
        with api_timeout(45, f"tushare.index_daily {target['ts_code']}"):
            df = pro.index_daily(ts_code=target["ts_code"], start_date=ts_start, end_date=ts_end)
        source = "tushare.index_daily"
    return normalize_index_history(df, target=target, target_type=target_type, source=source)


def fetch_akshare_history(
    target: dict[str, Any],
    target_type: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    import akshare as ak

    api_name = target.get("akshare_api")
    symbol = str(target.get("akshare_symbol", ""))
    start = date_token(start_date)
    end = date_token(end_date)
    if api_name == "stock_zh_index_hist_csindex":
        with api_timeout(45, f"akshare.{api_name} {symbol}"):
            df = ak.stock_zh_index_hist_csindex(symbol=symbol, start_date=start, end_date=end)
    elif api_name == "index_hist_cni":
        with api_timeout(45, f"akshare.{api_name} {symbol}"):
            try:
                df = ak.index_hist_cni(symbol=symbol, period="daily", start_date=start, end_date=end)
            except TypeError:
                df = ak.index_hist_cni(symbol=symbol, start_date=start, end_date=end)
    else:
        raise ValueError(f"No AKShare fallback configured for {target['target_key']}")
    return normalize_index_history(
        df,
        target=target,
        target_type=target_type,
        source=f"akshare.{api_name}",
    )


def command_prepare_universe(config: dict[str, Any]) -> list[Path]:
    for path in [
        config["paths"]["target_dir"],
        config["paths"]["cache_dir"],
        config["paths"]["report_dir"],
        config["paths"]["backtest_dir"],
        "Explore3/reports",
    ]:
        topic_path(path).mkdir(parents=True, exist_ok=True)
    universe_csv = topic_path(config["paths"]["universe_csv"])
    universe_qlib = topic_path(config["paths"]["universe_qlib"])
    shutil.copyfile(topic_path(config["paths"]["explore1_universe_csv"]), ensure_parent(universe_csv))
    shutil.copyfile(topic_path(config["paths"]["explore1_universe_qlib"]), ensure_parent(universe_qlib))
    outputs = [universe_csv, universe_qlib, *write_target_definitions(config)]
    universe = pd.read_csv(universe_csv)
    record_manifest(
        config,
        "prepare-universe",
        outputs,
        {
            "universe_instruments": int(universe["instrument"].nunique()),
            "universe_source": config["paths"]["explore1_universe_csv"],
        },
    )
    print(f"prepared universe rows={len(universe)} instruments={universe['instrument'].nunique()}", flush=True)
    return outputs


def fetch_industry_membership(config: dict[str, Any], pro) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    status_rows = []
    end = parse_dt(config["dates"]["data_end"])
    start = end - timedelta(days=550)
    for target in config["targets"]["industry"]:
        try:
            source = "tushare.index_weight"
            with api_timeout(45, f"tushare.index_weight {target['ts_code']}"):
                df = pro.index_weight(
                    index_code=target["ts_code"],
                    start_date=start.strftime("%Y%m%d"),
                    end_date=end.strftime("%Y%m%d"),
                )
            if df is None or df.empty:
                with api_timeout(45, f"tushare.index_member {target['ts_code']}"):
                    df = pro.index_member(index_code=target["ts_code"])
                source = "tushare.index_member"
            if df is None or df.empty:
                raise RuntimeError("empty industry membership response")
            if source == "tushare.index_weight":
                date_col = "trade_date" if "trade_date" in df.columns else "date"
                latest_date = str(df[date_col].max())
                latest = df[df[date_col].astype(str) == latest_date].copy()
            else:
                end_token = end.strftime("%Y%m%d")
                latest = df.copy()
                latest["in_date"] = latest["in_date"].fillna("00000000").astype(str)
                latest["out_date"] = latest["out_date"].fillna("").astype(str)
                latest = latest[
                    (latest["in_date"] <= end_token)
                    & ((latest["out_date"] == "") | (latest["out_date"].str.lower() == "none") | (latest["out_date"] >= end_token))
                ].copy()
                latest_date = end_token
                if latest.empty:
                    raise RuntimeError("empty active index_member response")
            con_col = "con_code" if "con_code" in latest.columns else "ts_code"
            weight_col = "weight" if "weight" in latest.columns else None
            for _, item in latest.iterrows():
                rows.append(
                    {
                        "instrument": ts_code_to_instrument(item[con_col]),
                        "stock_ts_code": item[con_col],
                        "industry_target_key": target["target_key"],
                        "industry_ts_code": target["ts_code"],
                        "industry_name": target["name"],
                        "source": source,
                        "source_trade_date": latest_date,
                        "weight": float(item[weight_col]) if weight_col and pd.notna(item[weight_col]) else np.nan,
                    }
                )
            status_rows.append(
                {
                    "industry_target_key": target["target_key"],
                    "industry_ts_code": target["ts_code"],
                    "status": "ok",
                    "rows": len(latest),
                    "source_trade_date": latest_date,
                    "source": source,
                    "error": "",
                }
            )
        except Exception as exc:  # noqa: BLE001
            status_rows.append(
                {
                    "industry_target_key": target["target_key"],
                    "industry_ts_code": target["ts_code"],
                    "status": "failed",
                    "rows": 0,
                    "source_trade_date": "",
                    "source": "",
                    "error": str(exc),
                }
            )
    membership = pd.DataFrame(rows)
    if not membership.empty:
        membership = membership.sort_values(["instrument", "industry_target_key"]).drop_duplicates(
            "instrument", keep="first"
        )
    else:
        membership = pd.DataFrame(
            columns=[
                "instrument",
                "stock_ts_code",
                "industry_target_key",
                "industry_ts_code",
                "industry_name",
                "source",
                "source_trade_date",
                "weight",
            ]
        )
    return membership, pd.DataFrame(status_rows)


def command_fetch_targets(config: dict[str, Any]) -> list[Path]:
    command_prepare_universe(config)
    pro = load_tushare_client(required=True)
    histories = []
    statuses = []
    start = config["dates"]["data_start"]
    end = config["dates"]["data_end"]
    for target_type in ["market", "industry", "theme"]:
        for target in config["targets"][target_type]:
            print(f"fetching {target_type}:{target['target_key']} {target['ts_code']}", flush=True)
            try:
                history = fetch_tushare_history(pro, target, target_type, start, end)
                if history.empty:
                    raise RuntimeError("empty Tushare response")
                statuses.append(
                    {
                        "target_type": target_type,
                        "target_key": target["target_key"],
                        "ts_code": target["ts_code"],
                        "status": "ok",
                        "source": history["source"].iloc[0],
                        "rows": len(history),
                        "start": history["date"].min().date().isoformat(),
                        "end": history["date"].max().date().isoformat(),
                        "error": "",
                    }
                )
                histories.append(history)
            except Exception as first_exc:  # noqa: BLE001
                if target_type in {"market", "theme"}:
                    try:
                        history = fetch_akshare_history(target, target_type, start, end)
                        if history.empty:
                            raise RuntimeError("empty AKShare response")
                        statuses.append(
                            {
                                "target_type": target_type,
                                "target_key": target["target_key"],
                                "ts_code": target["ts_code"],
                                "status": "ok_fallback",
                                "source": history["source"].iloc[0],
                                "rows": len(history),
                                "start": history["date"].min().date().isoformat(),
                                "end": history["date"].max().date().isoformat(),
                                "error": f"tushare failed: {first_exc}",
                            }
                        )
                        histories.append(history)
                        continue
                    except Exception as second_exc:  # noqa: BLE001
                        error = f"tushare failed: {first_exc}; akshare failed: {second_exc}"
                else:
                    error = str(first_exc)
                statuses.append(
                    {
                        "target_type": target_type,
                        "target_key": target["target_key"],
                        "ts_code": target["ts_code"],
                        "status": "failed",
                        "source": "",
                        "rows": 0,
                        "start": "",
                        "end": "",
                        "error": error,
                    }
                )
    if not histories:
        raise RuntimeError("No target history was fetched.")
    target_history = pd.concat(histories, ignore_index=True)
    history_path = write_csv(target_history, target_dir(config) / "target_history.csv")
    status_path = write_csv(pd.DataFrame(statuses), target_dir(config) / "target_fetch_status.csv")
    print("fetching industry membership with tushare.index_weight", flush=True)
    membership, membership_status = fetch_industry_membership(config, pro)
    membership_path = write_csv(membership, target_dir(config) / "industry_membership.csv")
    membership_status_path = write_csv(membership_status, target_dir(config) / "industry_membership_status.csv")
    outputs = [
        history_path,
        status_path,
        membership_path,
        membership_status_path,
        *write_target_definitions(config),
    ]
    broad = target_history[target_history["target_key"] == "broad_market"]
    if broad.empty:
        raise RuntimeError("broad_market target history is required but missing.")
    record_manifest(
        config,
        "fetch-targets",
        outputs,
        {
            "target_history_rows": int(len(target_history)),
            "target_fetch_failures": int((pd.DataFrame(statuses)["status"] == "failed").sum()),
            "industry_membership_rows": int(len(membership)),
            "industry_membership_failures": int((membership_status["status"] == "failed").sum()),
        },
    )
    print(
        "fetched targets "
        f"history_rows={len(target_history)} membership_rows={len(membership)} "
        f"failed_targets={(pd.DataFrame(statuses)['status'] == 'failed').sum()}",
        flush=True,
    )
    return outputs


def load_stock_panel_from_qlib(config: dict[str, Any]) -> pd.DataFrame:
    import qlib
    from qlib.constant import REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(topic_path(config["paths"]["provider_uri"])), region=REG_CN)
    df = D.features(
        instruments=D.instruments(config["qlib"]["market"]),
        fields=config["qlib"]["required_fields"],
        start_time=config["dates"]["data_start"],
        end_time=config["dates"]["data_end"],
        freq=config["costs"]["freq"],
    )
    if df.empty:
        raise RuntimeError("Qlib provider returned no stock data.")
    df = df.rename(columns=FIELD_RENAME).reset_index()
    df["instrument"] = df["instrument"].astype(str).str.upper()
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df.sort_values(["instrument", "datetime"]).reset_index(drop=True)


def stock_panel_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_panel.pkl"


def load_stock_panel(config: dict[str, Any]) -> pd.DataFrame:
    path = stock_panel_cache_path(config)
    if path.exists():
        return pd.read_pickle(path)
    df = load_stock_panel_from_qlib(config)
    ensure_parent(path)
    pd.to_pickle(df, path)
    return df


def command_validate_cache(config: dict[str, Any]) -> list[Path]:
    command_prepare_universe(config)
    universe = pd.read_csv(topic_path(config["paths"]["universe_csv"]))
    panel = load_stock_panel_from_qlib(config)
    ensure_parent(stock_panel_cache_path(config))
    pd.to_pickle(panel, stock_panel_cache_path(config))
    required = [FIELD_RENAME[field] for field in config["qlib"]["required_fields"]]
    rows = []
    for instrument, group in panel.groupby("instrument", sort=True):
        row = {
            "instrument": instrument,
            "rows": int(len(group)),
            "start": group["datetime"].min().date().isoformat(),
            "end": group["datetime"].max().date().isoformat(),
            "missing_values": int(group[required].isna().sum().sum()),
            "missing_fields": ",".join([col for col in required if group[col].notna().sum() == 0]),
            "duplicate_dates": int(group["datetime"].duplicated().sum()),
        }
        row["status"] = "ok" if row["rows"] > 0 and not row["missing_fields"] else "failed"
        rows.append(row)
    coverage = pd.DataFrame(rows)
    expected = set(universe["instrument"].astype(str).str.upper())
    found = set(coverage["instrument"])
    missing_rows = [
        {
            "instrument": instrument,
            "rows": 0,
            "start": "",
            "end": "",
            "missing_values": 0,
            "missing_fields": ",".join(required),
            "duplicate_dates": 0,
            "status": "failed",
        }
        for instrument in sorted(expected.difference(found))
    ]
    if missing_rows:
        coverage = pd.concat([coverage, pd.DataFrame(missing_rows)], ignore_index=True)
    data_quality_path = write_csv(coverage, report_dir(config) / "data_quality_report.csv")
    coverage_path = write_csv(coverage, report_dir(config) / "explore1_cache_coverage.csv")
    failed = coverage[coverage["status"] == "failed"]
    record_manifest(
        config,
        "validate-cache",
        [stock_panel_cache_path(config), data_quality_path, coverage_path],
        {
            "stock_cache_rows": int(len(panel)),
            "stock_cache_instruments": int(panel["instrument"].nunique()),
            "stock_cache_start": panel["datetime"].min().date().isoformat(),
            "stock_cache_end": panel["datetime"].max().date().isoformat(),
            "stock_cache_failed_instruments": int(len(failed)),
        },
    )
    if not failed.empty:
        raise RuntimeError(f"Qlib cache validation failed for {len(failed)} instruments.")
    print(f"validated stock cache rows={len(panel)} instruments={panel['instrument'].nunique()}", flush=True)
    return [data_quality_path, coverage_path]


def add_group_indicators(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    df = df.sort_values(["instrument", "datetime"])
    group = df.groupby("instrument", group_keys=False)
    for span in [20, 30, 60, 120]:
        df[f"ema{span}"] = group["close"].transform(lambda s, span=span: s.ewm(span=span, adjust=False).mean())
    prev_close = group["close"].shift(1)
    tr_parts = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    df["true_range"] = tr_parts.max(axis=1)
    df["atr20"] = group["true_range"].transform(lambda s: s.rolling(20, min_periods=5).mean())
    df["ret1"] = group["close"].pct_change()
    df["ret20"] = group["close"].pct_change(20)
    df["ret60"] = group["close"].pct_change(60)
    df["volatility20"] = group["ret1"].transform(lambda s: s.rolling(20, min_periods=10).std())
    df["avg_money20"] = group["money"].transform(lambda s: s.rolling(20, min_periods=5).mean())
    df["money_ratio20"] = df["money"] / df["avg_money20"].replace(0, np.nan)
    df["ema60_slope10"] = df["ema60"] / group["ema60"].shift(10) - 1.0
    df["ema60_slope20"] = df["ema60"] / group["ema60"].shift(20) - 1.0
    df["ema20_ema60_spread"] = df["ema20"] / df["ema60"] - 1.0
    df["dist_ema20"] = (df["close"] - df["ema20"]) / df["close"]
    df["rolling_high60"] = group["close"].transform(lambda s: s.shift(1).rolling(60, min_periods=20).max())
    df["rolling_low20"] = group["low"].transform(lambda s: s.shift(1).rolling(20, min_periods=5).min())
    df["recent_low5"] = group["low"].transform(lambda s: s.shift(1).rolling(5, min_periods=2).min())
    df["range"] = (df["high"] - df["low"]).replace(0, np.nan)
    df["close_pos"] = (df["close"] - df["low"]) / df["range"]
    df["upper_shadow_pct"] = (df["high"] - df[["open", "close"]].max(axis=1)) / df["range"]
    df["overheat"] = (df["close"] / df["ema20"] - 1.0).clip(lower=0)
    df["adx_proxy20"] = (df["ret20"].abs() / df["volatility20"].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    return df


def target_history_path(config: dict[str, Any]) -> Path:
    return target_dir(config) / "target_history.csv"


def load_target_history(config: dict[str, Any]) -> pd.DataFrame:
    path = target_history_path(config)
    if not path.exists():
        raise FileNotFoundError(f"{relpath(path)} missing. Run fetch-targets first.")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    return df


def compute_target_regimes(config: dict[str, Any], history: pd.DataFrame) -> pd.DataFrame:
    market_rules = config["rules"]["market"]
    df = history.sort_values(["target_key", "date"]).copy()
    group = df.groupby("target_key", group_keys=False)
    df["ema60"] = group["close"].transform(lambda s: s.ewm(span=market_rules["ema"], adjust=False).mean())
    df["ema120"] = group["close"].transform(lambda s: s.ewm(span=market_rules["record_ema"], adjust=False).mean())
    df["ema60_slope20"] = df["ema60"] / group["ema60"].shift(market_rules["slope_window"]) - 1.0
    df["ret60"] = group["close"].pct_change(60)
    broad = (
        df[df["target_key"] == "broad_market"][["date", "ret60"]]
        .rename(columns={"ret60": "broad_ret60"})
        .drop_duplicates("date")
    )
    df = df.merge(broad, on="date", how="left")
    df["close_gt_ema60"] = df["close"] > df["ema60"]
    df["close_gt_ema120"] = df["close"] > df["ema120"]
    df["ema60_slope20_gt0"] = df["ema60_slope20"] > 0
    df["ret60_gt_broad"] = df["ret60"] > df["broad_ret60"]
    df["trend_ok"] = df["close_gt_ema60"] & df["ema60_slope20_gt0"]
    df.loc[df["target_key"] != "broad_market", "trend_ok"] = (
        df["trend_ok"] & df["ret60_gt_broad"]
    )
    return df


def compute_market_width(config: dict[str, Any], indicators: pd.DataFrame) -> pd.DataFrame:
    width_rules = config["rules"]["width"]
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
    width["width_ok"] = (
        (width["close_gt_ema60_ratio"] > width_rules["close_gt_ema60"])
        & (width["ema20_gt_ema60_ratio"] > width_rules["ema20_gt_ema60"])
    )
    return width.rename(columns={"datetime": "date"})


def stock_indicators_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_indicators.pkl"


def command_build_regimes(config: dict[str, Any]) -> list[Path]:
    if not target_history_path(config).exists():
        command_fetch_targets(config)
    panel = load_stock_panel(config)
    indicators = add_group_indicators(panel)
    ensure_parent(stock_indicators_cache_path(config))
    pd.to_pickle(indicators, stock_indicators_cache_path(config))
    target_regimes = compute_target_regimes(config, load_target_history(config))
    width = compute_market_width(config, indicators)
    market = target_regimes[target_regimes["target_type"] == "market"].merge(width, on="date", how="left")
    broad_market_ok = market[market["target_key"] == "broad_market"][["date", "trend_ok"]].rename(
        columns={"trend_ok": "market_ok"}
    )
    market = market.merge(broad_market_ok, on="date", how="left")
    industry = target_regimes[target_regimes["target_type"] == "industry"].rename(
        columns={"trend_ok": "industry_trend_ok"}
    )
    theme = target_regimes[target_regimes["target_type"] == "theme"].rename(columns={"trend_ok": "theme_trend_ok"})
    market_path = write_csv(market, report_dir(config) / "market_regime.csv")
    width_path = write_csv(width, report_dir(config) / "market_width.csv")
    industry_path = write_csv(industry, report_dir(config) / "industry_regime.csv")
    theme_path = write_csv(theme, report_dir(config) / "theme_regime.csv")
    outputs = [stock_indicators_cache_path(config), market_path, width_path, industry_path, theme_path]
    record_manifest(
        config,
        "build-regimes",
        outputs,
        {
            "stock_indicator_rows": int(len(indicators)),
            "market_regime_rows": int(len(market)),
            "industry_regime_rows": int(len(industry)),
            "theme_regime_rows": int(len(theme)),
        },
    )
    print(
        f"built regimes stock_rows={len(indicators)} market_rows={len(market)} "
        f"industry_rows={len(industry)} theme_rows={len(theme)}",
        flush=True,
    )
    return outputs


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


def load_industry_membership(config: dict[str, Any]) -> pd.DataFrame:
    path = target_dir(config) / "industry_membership.csv"
    if not path.exists():
        return pd.DataFrame(columns=["instrument", "industry_target_key", "industry_name"])
    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame(columns=["instrument", "industry_target_key", "industry_name"])
    df["instrument"] = df["instrument"].astype(str).str.upper()
    return df


def stock_signal_cache_path(config: dict[str, Any]) -> Path:
    return cache_dir(config) / "stock_signals.pkl"


def command_build_signals(config: dict[str, Any]) -> list[Path]:
    if not stock_indicators_cache_path(config).exists():
        command_build_regimes(config)
    df = pd.read_pickle(stock_indicators_cache_path(config)).copy()
    market = pd.read_csv(report_dir(config) / "market_regime.csv")
    market["date"] = pd.to_datetime(market["date"])
    broad = market[market["target_key"] == "broad_market"][
        ["date", "market_ok", "width_ok", "ret60"]
    ].rename(columns={"date": "datetime", "ret60": "broad_ret60"})
    df = df.merge(broad, on="datetime", how="left")
    membership = load_industry_membership(config)
    if not membership.empty:
        df = df.merge(
            membership[["instrument", "industry_target_key", "industry_name"]],
            on="instrument",
            how="left",
        )
    else:
        df["industry_target_key"] = pd.Series(pd.NA, index=df.index, dtype="string")
        df["industry_name"] = pd.Series(pd.NA, index=df.index, dtype="string")
    df["industry_target_key"] = df["industry_target_key"].astype("string")
    industry = pd.read_csv(report_dir(config) / "industry_regime.csv")
    if not industry.empty:
        industry["date"] = pd.to_datetime(industry["date"])
        industry = industry[["date", "target_key", "industry_trend_ok"]].rename(
            columns={"date": "datetime", "target_key": "industry_target_key"}
        )
        industry["industry_target_key"] = industry["industry_target_key"].astype("string")
        df = df.merge(industry, on=["datetime", "industry_target_key"], how="left")
    else:
        df["industry_trend_ok"] = False
    theme = pd.read_csv(report_dir(config) / "theme_regime.csv")
    theme["date"] = pd.to_datetime(theme["date"])
    theme_daily = (
        theme.groupby("date", as_index=False)
        .agg(theme_positive_count=("theme_trend_ok", "sum"), theme_count=("target_key", "count"))
        .rename(columns={"date": "datetime"})
    )
    df = df.merge(theme_daily, on="datetime", how="left")

    candidate_rules = config["rules"]["candidate"]
    df["ret60_excess"] = df["ret60"] - df["broad_ret60"]
    df["volatility20_p90"] = df.groupby("datetime")["volatility20"].transform(
        lambda s: s.quantile(candidate_rules["volatility_quantile"])
    )
    df["avg_money20_p20"] = df.groupby("datetime")["avg_money20"].transform(
        lambda s: s.quantile(candidate_rules["money_quantile"])
    )
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
    df["width_ok_entry"] = df["market_ok_entry"] & df["width_ok"].fillna(False)
    df["industry_ok_entry"] = df["width_ok_entry"] & df["industry_trend_ok"].fillna(False)

    score_rules = config["rules"]["score"]
    for component in score_rules["weights"]:
        z_col = f"z_{component}"
        df[z_col] = daily_zscore(df, component, score_rules["winsor_lower"], score_rules["winsor_upper"])
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
    pullback = config["rules"]["pullback"]
    near_ema20 = df["low"] <= df["ema20"] * (1 + pullback["ema_band_pct"])
    near_ema30 = df["low"] <= df["ema30"] * (1 + pullback["ema_band_pct"])
    df["pullback_entry"] = (
        df["trend_score_top20_entry"]
        & (near_ema20 | near_ema30)
        & (df["low"] > df["ema60"])
        & (df["money_ratio20"] <= 1.0)
        & (df["close"] >= df["ema20"])
        & (df["close"] > df["open"])
    )
    df["combined_entry"] = df["breakout_entry"] | df["pullback_entry"]

    ensure_parent(stock_signal_cache_path(config))
    pd.to_pickle(df, stock_signal_cache_path(config))

    count_cols = [
        "ema_state",
        "market_ok_entry",
        "width_ok_entry",
        "industry_ok_entry",
        "trend_score_top20_entry",
        "breakout_entry",
        "pullback_entry",
        "combined_entry",
    ]
    daily = df.groupby("datetime", as_index=False).agg(
        instruments=("instrument", "nunique"),
        **{col: (col, "sum") for col in count_cols},
        trend_score_median=("trend_score", "median"),
        trend_score_p90=("trend_score", lambda s: s.quantile(0.9)),
        theme_positive_count=("theme_positive_count", "max"),
    )
    daily_path = write_csv(daily, report_dir(config) / "daily_candidates.csv")
    score_cols = [
        "datetime",
        "instrument",
        "industry_name",
        "ema_state",
        "industry_ok_entry",
        "trend_score",
        "trend_score_pct",
        "ret20",
        "ret60",
        "ret60_excess",
        "money_ratio20",
        "volatility20",
        "overheat",
    ]
    scores = df.loc[df["ema_state"], score_cols].copy()
    scores_path = write_csv(scores, report_dir(config) / "daily_scores.csv")
    signal_cols = [
        "datetime",
        "instrument",
        "industry_name",
        "ema_state",
        "market_ok_entry",
        "width_ok_entry",
        "industry_ok_entry",
        "trend_score_top20_entry",
        "breakout_entry",
        "pullback_entry",
        "combined_entry",
        "trend_score",
        "trend_score_pct",
        "rolling_high60",
        "rolling_low20",
        "recent_low5",
        "atr20",
        "ema20",
        "ema60",
    ]
    signals = df.loc[df[count_cols].any(axis=1), signal_cols].copy()
    signals_path = write_csv(signals, report_dir(config) / "signals.csv")
    outputs = [stock_signal_cache_path(config), daily_path, scores_path, signals_path]
    record_manifest(
        config,
        "build-signals",
        outputs,
        {
            "signal_rows": int(len(signals)),
            "daily_score_rows": int(len(scores)),
            "industry_mapped_instruments": int(df["industry_target_key"].notna().groupby(df["instrument"]).max().sum()),
        },
    )
    print(f"built signals rows={len(signals)} score_rows={len(scores)}", flush=True)
    return outputs


def next_trading_date(dates: list[pd.Timestamp], index: int) -> pd.Timestamp | None:
    return dates[index + 1] if index + 1 < len(dates) else None


def is_limit_blocked(row: pd.Series, direction: str, limit_threshold: float) -> bool:
    prev_close = row.get("prev_close_for_limit")
    price = row.get("open")
    if pd.isna(prev_close) or pd.isna(price) or prev_close <= 0:
        return False
    if direction == "buy":
        return price >= prev_close * (1 + limit_threshold)
    return price <= prev_close * (1 - limit_threshold)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def initial_stop_for(row: pd.Series, entry_price: float, entry_type: str, stop_mode: str, config: dict[str, Any]) -> float:
    stop_rules = config["rules"]["stops"]
    if stop_mode == "atr_structure":
        atr = safe_float(row.get("atr20"), entry_price * stop_rules["fixed_stop_pct"])
        if entry_type == "breakout":
            stop = safe_float(row.get("rolling_low20"), entry_price - stop_rules["atr_multiplier"] * atr)
        elif entry_type == "pullback":
            stop = safe_float(row.get("recent_low5"), entry_price - stop_rules["atr_multiplier"] * atr)
        else:
            stop = entry_price - stop_rules["atr_multiplier"] * atr
        stop -= stop_rules["structure_atr_buffer"] * atr
        if stop <= 0 or stop >= entry_price:
            stop = entry_price - stop_rules["atr_multiplier"] * atr
        return max(0.01, stop)
    return max(0.01, entry_price * (1 - stop_rules["fixed_stop_pct"]))


def choose_entry_type(row: pd.Series, ablation: dict[str, Any]) -> str:
    configured = ablation["entry_type"]
    if configured == "combined":
        if bool(row.get("breakout_entry", False)):
            return "breakout"
        if bool(row.get("pullback_entry", False)):
            return "pullback"
        return "combined"
    return configured


def trade_return(entry_price: float, exit_price: float, entry_cost: float, exit_cost: float, amount: float) -> tuple[float, float]:
    if entry_price <= 0 or amount <= 0:
        return 0.0, 0.0
    gross = (exit_price - entry_price) / entry_price
    entry_value = entry_price * amount
    exit_value = exit_price * amount
    net = (exit_value - exit_cost - entry_value - entry_cost) / (entry_value + entry_cost)
    return gross, net


def round_lot_amount(value: float, price: float) -> int:
    if price <= 0 or value <= 0:
        return 0
    return int(value // (price * 100)) * 100


def empty_trade_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=REPORT_COLUMNS)


def compute_metrics(
    version: str,
    portfolio: pd.DataFrame,
    trades: pd.DataFrame,
    account: float,
) -> dict[str, Any]:
    if portfolio.empty:
        return {"version": version, "trades": 0}
    report = portfolio.copy()
    total_with_cost = report["account_value"].iloc[-1] / account - 1
    return_without_cost = report["return"].fillna(0) + report["cost"].fillna(0) / report["prev_account_value"].replace(0, np.nan)
    total_without_cost = float((1 + return_without_cost.fillna(0)).prod() - 1)
    running_max = report["account_value"].cummax()
    drawdown = report["account_value"] / running_max - 1
    days = max(len(report), 1)
    annual = (1 + total_with_cost) ** (252 / days) - 1 if total_with_cost > -1 else -1
    closed = trades[trades["exit_reason"].fillna("") != "open"] if not trades.empty else trades
    wins = closed[pd.to_numeric(closed.get("cost_after_return"), errors="coerce") > 0] if not closed.empty else closed
    losses = closed[pd.to_numeric(closed.get("cost_after_return"), errors="coerce") <= 0] if not closed.empty else closed
    top5_profit = (
        pd.to_numeric(closed.get("cost_after_return"), errors="coerce").sort_values(ascending=False).head(5).sum()
        if not closed.empty
        else 0.0
    )
    return {
        "version": version,
        "rows": int(len(report)),
        "trades": int(len(closed)),
        "win_rate": float(len(wins) / len(closed)) if len(closed) else 0.0,
        "avg_profit": float(pd.to_numeric(wins.get("cost_after_return"), errors="coerce").mean())
        if len(wins)
        else 0.0,
        "avg_loss": float(pd.to_numeric(losses.get("cost_after_return"), errors="coerce").mean())
        if len(losses)
        else 0.0,
        "avg_holding_days": float(pd.to_numeric(closed.get("holding_days"), errors="coerce").mean())
        if len(closed)
        else 0.0,
        "total_return_with_cost": float(total_with_cost),
        "total_return_without_cost": float(total_without_cost),
        "annual_return_with_cost": float(annual),
        "max_drawdown": float(drawdown.min()),
        "return_drawdown_ratio": float(annual / abs(drawdown.min())) if drawdown.min() < 0 else np.nan,
        "turnover_mean": float(report["turnover"].mean()),
        "cost_mean": float(report["cost"].mean()),
        "ending_account": float(report["account_value"].iloc[-1]),
        "breakout_trades": int((closed.get("entry_type", pd.Series(dtype=str)) == "breakout").sum()),
        "pullback_trades": int((closed.get("entry_type", pd.Series(dtype=str)) == "pullback").sum()),
        "stop_exit_ratio": float(closed["exit_reason"].str.contains("stop", na=False).mean()) if len(closed) else 0.0,
        "time_stop_exit_ratio": float((closed.get("exit_reason", pd.Series(dtype=str)) == "time_stop").mean())
        if len(closed)
        else 0.0,
        "ema60_exit_ratio": float((closed.get("exit_reason", pd.Series(dtype=str)) == "ema60_exit").mean())
        if len(closed)
        else 0.0,
        "top5_trade_return_sum": float(top5_profit),
    }


def run_backtest_one(config: dict[str, Any], signals: pd.DataFrame, ablation: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    version = ablation["version"]
    entry_filter = ablation["entry_filter"]
    stop_mode = ablation["stop_mode"]
    exit_mode = ablation["exit_mode"]
    costs = config["costs"]
    portfolio_rules = config["rules"]["portfolio"]
    stop_rules = config["rules"]["stops"]
    start = parse_dt(config["dates"]["backtest_start"])
    end = parse_dt(config["dates"]["backtest_end"])
    data_end = parse_dt(config["dates"]["data_end"])
    df = signals.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values(["datetime", "instrument"])
    df["prev_close_for_limit"] = df.groupby("instrument")["close"].shift(1)
    all_dates = sorted(df[(df["datetime"] >= start) & (df["datetime"] <= data_end)]["datetime"].unique())
    all_dates = [pd.Timestamp(date) for date in all_dates]
    by_date = {date: day.set_index("instrument", drop=False) for date, day in df[df["datetime"].isin(all_dates)].groupby("datetime")}
    cash = float(costs["account"])
    positions: dict[str, dict[str, Any]] = {}
    pending: dict[pd.Timestamp, list[dict[str, Any]]] = {}
    trade_rows: list[dict[str, Any]] = []
    portfolio_rows: list[dict[str, Any]] = []
    previous_value = cash
    target_weight = min(
        float(portfolio_rules["single_stock_max_weight"]),
        float(portfolio_rules["risk_degree"]) / int(portfolio_rules["max_positions"]),
    )
    max_positions = int(portfolio_rules["max_positions"])
    max_daily_new_weight = float(portfolio_rules["max_daily_new_weight"])

    def schedule(date: pd.Timestamp, order: dict[str, Any]) -> None:
        pending.setdefault(date, []).append(order)

    for idx, date in enumerate(all_dates):
        day = by_date[date]
        day_cost = 0.0
        day_turnover = 0.0
        orders = pending.pop(date, [])
        sells = [order for order in orders if order["direction"] == "sell"]
        buys = [order for order in orders if order["direction"] == "buy"]
        for order in sells + buys:
            instrument = order["instrument"]
            if instrument not in day.index:
                continue
            row = day.loc[instrument]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            price = safe_float(row.get("open"))
            if price <= 0 or is_limit_blocked(row, order["direction"], float(costs["limit_threshold"])):
                continue
            if order["direction"] == "sell":
                position = positions.pop(instrument, None)
                if not position:
                    continue
                amount = position["amount"]
                value = amount * price
                cost = max(value * float(costs["close_cost"]), float(costs["min_cost"]))
                cash += value - cost
                day_cost += cost
                day_turnover += value
                gross, net = trade_return(position["entry_price"], price, position["entry_cost"], cost, amount)
                trade_rows.append(
                    {
                        "instrument": instrument,
                        "signal_date": position["signal_date"].date().isoformat(),
                        "order_date": position["order_date"].date().isoformat(),
                        "deal_date": position["deal_date"].date().isoformat(),
                        "entry_type": position["entry_type"],
                        "entry_price": position["entry_price"],
                        "exit_signal_date": order["signal_date"].date().isoformat(),
                        "exit_date": date.date().isoformat(),
                        "exit_price": price,
                        "initial_stop": position["initial_stop"],
                        "current_stop": position["current_stop"],
                        "R": position["R"],
                        "exit_reason": order["exit_reason"],
                        "holding_days": int((date - position["deal_date"]).days),
                        "cost_before_return": gross,
                        "cost_after_return": net,
                    }
                )
            else:
                if instrument in positions:
                    continue
                budget = min(order["budget"], cash)
                amount = round_lot_amount(budget, price)
                if amount <= 0:
                    continue
                value = amount * price
                cost = max(value * float(costs["open_cost"]), float(costs["min_cost"]))
                if value + cost > cash:
                    amount = round_lot_amount(cash - float(costs["min_cost"]), price)
                    value = amount * price
                    cost = max(value * float(costs["open_cost"]), float(costs["min_cost"]))
                if amount <= 0 or value + cost > cash:
                    continue
                signal_row = order["signal_row"]
                entry_type = order["entry_type"]
                stop = initial_stop_for(signal_row, price, entry_type, stop_mode, config)
                risk = max(price - stop, price * 0.01)
                cash -= value + cost
                day_cost += cost
                day_turnover += value
                positions[instrument] = {
                    "amount": amount,
                    "entry_price": price,
                    "entry_cost": cost,
                    "signal_date": order["signal_date"],
                    "order_date": date,
                    "deal_date": date,
                    "entry_type": entry_type,
                    "initial_stop": stop,
                    "current_stop": stop,
                    "R": risk,
                }

        if date <= end:
            next_date = next_trading_date(all_dates, idx)
            if next_date is not None:
                exiting = set()
                for instrument, position in list(positions.items()):
                    if instrument not in day.index:
                        continue
                    row = day.loc[instrument]
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[0]
                    close = safe_float(row.get("close"))
                    if close <= 0:
                        continue
                    unreal_r = (close - position["entry_price"]) / position["R"]
                    if exit_mode == "layered":
                        if unreal_r >= 1:
                            position["current_stop"] = max(position["current_stop"], position["entry_price"])
                        if unreal_r >= 2:
                            atr = safe_float(row.get("atr20"))
                            trail = max(safe_float(row.get("ema20")), close - stop_rules["trailing_atr_multiplier"] * atr)
                            position["current_stop"] = max(position["current_stop"], trail)
                        if unreal_r >= 3 and safe_float(row.get("dist_ema20")) > 0.10:
                            position["current_stop"] = max(position["current_stop"], safe_float(row.get("ema20")))
                    exit_reason = ""
                    if close <= position["current_stop"]:
                        exit_reason = "trailing_stop" if position["current_stop"] >= position["entry_price"] else "stop_loss"
                    holding_days = int((date - position["deal_date"]).days)
                    if not exit_reason and holding_days >= stop_rules["time_stop_days"] and close <= position["entry_price"]:
                        exit_reason = "time_stop"
                    if not exit_reason and close < safe_float(row.get("ema60")):
                        exit_reason = "ema60_exit"
                    if not exit_reason and exit_mode == "ema_fixed" and safe_float(row.get("ema20")) <= safe_float(row.get("ema60")):
                        exit_reason = "ema_cross_exit"
                    if exit_reason:
                        exiting.add(instrument)
                        schedule(
                            next_date,
                            {
                                "direction": "sell",
                                "instrument": instrument,
                                "signal_date": date,
                                "exit_reason": exit_reason,
                            },
                        )

                current_value = cash + sum(
                    pos["amount"]
                    * safe_float(day.loc[inst].iloc[0]["close"] if isinstance(day.loc[inst], pd.DataFrame) else day.loc[inst]["close"])
                    for inst, pos in positions.items()
                    if inst in day.index
                )
                available_slots = max_positions - len(positions) - len(
                    [order for orders in pending.values() for order in orders if order["direction"] == "buy"]
                )
                if available_slots > 0:
                    candidates = day[day[entry_filter].fillna(False)].copy() if entry_filter in day.columns else day.iloc[0:0]
                    candidates = candidates[~candidates["instrument"].isin(set(positions) | exiting)]
                    if not candidates.empty:
                        if "trend_score" in candidates.columns and candidates["trend_score"].notna().any():
                            candidates = candidates.sort_values(["trend_score", "ret60", "money_ratio20"], ascending=False)
                        else:
                            candidates = candidates.sort_values(["ret60", "money_ratio20"], ascending=False)
                    daily_budget = current_value * max_daily_new_weight
                    per_order_budget = current_value * target_weight
                    used_budget = 0.0
                    for _, candidate in candidates.head(max_positions).iterrows():
                        if available_slots <= 0 or used_budget >= daily_budget:
                            break
                        budget = min(per_order_budget, daily_budget - used_budget)
                        if budget <= 0:
                            break
                        entry_type = choose_entry_type(candidate, ablation)
                        schedule(
                            next_date,
                            {
                                "direction": "buy",
                                "instrument": candidate["instrument"],
                                "signal_date": date,
                                "entry_type": entry_type,
                                "budget": budget,
                                "signal_row": candidate,
                            },
                        )
                        used_budget += budget
                        available_slots -= 1

        position_value = 0.0
        for instrument, position in positions.items():
            if instrument in day.index:
                row = day.loc[instrument]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                position_value += position["amount"] * safe_float(row.get("close"))
        account_value = cash + position_value
        if date <= end:
            portfolio_rows.append(
                {
                    "datetime": date.date().isoformat(),
                    "cash": cash,
                    "position_value": position_value,
                    "account_value": account_value,
                    "prev_account_value": previous_value,
                    "return": account_value / previous_value - 1 if previous_value else 0.0,
                    "cost": day_cost,
                    "turnover": day_turnover / previous_value if previous_value else 0.0,
                    "positions": len(positions),
                }
            )
            previous_value = account_value

    final_exit_date = None
    for date in all_dates:
        if date > end:
            final_exit_date = date
            break
    if final_exit_date is not None and positions:
        day = by_date[final_exit_date]
        for instrument, position in list(positions.items()):
            if instrument not in day.index:
                continue
            row = day.loc[instrument]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            price = safe_float(row.get("open"), safe_float(row.get("close")))
            amount = position["amount"]
            value = amount * price
            cost = max(value * float(costs["close_cost"]), float(costs["min_cost"]))
            gross, net = trade_return(position["entry_price"], price, position["entry_cost"], cost, amount)
            trade_rows.append(
                {
                    "instrument": instrument,
                    "signal_date": position["signal_date"].date().isoformat(),
                    "order_date": position["order_date"].date().isoformat(),
                    "deal_date": position["deal_date"].date().isoformat(),
                    "entry_type": position["entry_type"],
                    "entry_price": position["entry_price"],
                    "exit_signal_date": end.date().isoformat(),
                    "exit_date": final_exit_date.date().isoformat(),
                    "exit_price": price,
                    "initial_stop": position["initial_stop"],
                    "current_stop": position["current_stop"],
                    "R": position["R"],
                    "exit_reason": "end_of_backtest",
                    "holding_days": int((final_exit_date - position["deal_date"]).days),
                    "cost_before_return": gross,
                    "cost_after_return": net,
                }
            )
        positions.clear()

    portfolio = pd.DataFrame(portfolio_rows)
    trades = pd.DataFrame(trade_rows, columns=REPORT_COLUMNS) if trade_rows else empty_trade_frame()
    metrics = compute_metrics(version, portfolio, trades, float(costs["account"]))
    return portfolio, trades, metrics


def command_run_ablation(config: dict[str, Any]) -> list[Path]:
    if not stock_signal_cache_path(config).exists():
        command_build_signals(config)
    signals = pd.read_pickle(stock_signal_cache_path(config))
    outputs: list[Path] = []
    summaries = []
    all_trades = []
    for ablation in config["ablations"]:
        version = ablation["version"]
        portfolio, trades, metrics = run_backtest_one(config, signals, ablation)
        version_dir = topic_path(config["paths"]["backtest_dir"]) / version
        portfolio_path = write_csv(portfolio, version_dir / "portfolio_daily.csv")
        trades_path = write_csv(trades, version_dir / "trade_detail.csv")
        outputs.extend([portfolio_path, trades_path])
        summaries.append(metrics)
        if not trades.empty:
            trades_with_version = trades.copy()
            trades_with_version.insert(0, "version", version)
            all_trades.append(trades_with_version)
        print(
            f"ran {version} trades={metrics.get('trades', 0)} "
            f"return={metrics.get('total_return_with_cost', 0):.4f}",
            flush=True,
        )
    summary = pd.DataFrame(summaries)
    summary_path = write_csv(summary, report_dir(config) / "trend_rule_ablation_summary.csv")
    if all_trades:
        detail = pd.concat(all_trades, ignore_index=True)
    else:
        detail = pd.DataFrame(columns=["version", *REPORT_COLUMNS])
    detail_path = write_csv(detail, report_dir(config) / "trade_detail.csv")
    outputs.extend([summary_path, detail_path])
    record_manifest(
        config,
        "run-ablation",
        outputs,
        {
            "ablation_versions": [row["version"] for row in summaries],
            "ablation_summary_rows": int(len(summary)),
            "trade_detail_rows": int(len(detail)),
        },
    )
    return outputs


def format_pct(value: Any) -> str:
    number = safe_float(value, np.nan)
    if pd.isna(number):
        return "NA"
    return f"{number:.2%}"


def format_number(value: Any, digits: int = 4) -> str:
    number = safe_float(value, np.nan)
    if pd.isna(number):
        return "NA"
    return f"{number:.{digits}f}"


def format_money(value: Any) -> str:
    number = safe_float(value, np.nan)
    if pd.isna(number):
        return "NA"
    return f"{number:,.2f}"


def format_int(value: Any) -> str:
    number = safe_float(value, np.nan)
    if pd.isna(number):
        return "NA"
    return f"{int(round(number)):,}"


def read_csv_if_exists(path: str | Path, **kwargs) -> pd.DataFrame:
    target = topic_path(path)
    return pd.read_csv(target, **kwargs) if target.exists() else pd.DataFrame()


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    output = ["| " + " | ".join(headers) + " |"]
    output.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        output.append("| " + " | ".join(str(value) for value in row) + " |")
    return output


def portfolio_year_rows(config: dict[str, Any], versions: list[str]) -> list[list[str]]:
    rows = []
    for version in versions:
        path = topic_path(config["paths"]["backtest_dir"]) / version / "portfolio_daily.csv"
        if not path.exists():
            continue
        portfolio = pd.read_csv(path, parse_dates=["datetime"])
        if portfolio.empty:
            continue
        portfolio["year"] = portfolio["datetime"].dt.year
        for year, group in portfolio.groupby("year", sort=True):
            base = safe_float(group["prev_account_value"].iloc[0])
            end_value = safe_float(group["account_value"].iloc[-1])
            ret = end_value / base - 1 if base else np.nan
            running_max = group["account_value"].cummax()
            drawdown = group["account_value"] / running_max - 1
            rows.append(
                [
                    version,
                    str(year),
                    format_pct(ret),
                    format_pct(drawdown.min()),
                    format_number(group["turnover"].mean(), 4),
                    format_money(group["cost"].sum()),
                    format_money(end_value),
                ]
            )
    return rows


def summarize_trade_group(group: pd.DataFrame, label_cols: list[str]) -> list[list[str]]:
    if group.empty:
        return []
    result = []
    grouped = group.groupby(label_cols, dropna=False)
    for key, subset in grouped:
        key_values = list(key) if isinstance(key, tuple) else [key]
        ret = pd.to_numeric(subset["cost_after_return"], errors="coerce")
        gross = pd.to_numeric(subset["cost_before_return"], errors="coerce")
        holding = pd.to_numeric(subset["holding_days"], errors="coerce")
        result.append(
            [
                *[str(value) for value in key_values],
                format_int(len(subset)),
                format_pct((ret > 0).mean() if len(subset) else np.nan),
                format_pct(ret.mean()),
                format_pct(gross.mean()),
                format_number(holding.mean(), 1),
                format_pct(ret.sum()),
            ]
        )
    return result


def safe_min(series: pd.Series) -> str:
    cleaned = series.replace("", np.nan).dropna()
    return str(cleaned.min()) if not cleaned.empty else "NA"


def safe_max(series: pd.Series) -> str:
    cleaned = series.replace("", np.nan).dropna()
    return str(cleaned.max()) if not cleaned.empty else "NA"


def command_report(config: dict[str, Any]) -> list[Path]:
    summary_path = report_dir(config) / "trend_rule_ablation_summary.csv"
    if not summary_path.exists():
        command_run_ablation(config)
    summary = pd.read_csv(summary_path)
    manifest = read_json(manifest_path(config))
    data_quality = read_csv_if_exists(report_dir(config) / "explore1_cache_coverage.csv")
    target_status = read_csv_if_exists(target_dir(config) / "target_fetch_status.csv")
    membership_status = read_csv_if_exists(target_dir(config) / "industry_membership_status.csv")
    membership = read_csv_if_exists(target_dir(config) / "industry_membership.csv")
    universe = read_csv_if_exists(config["paths"]["universe_csv"])
    candidates = read_csv_if_exists(report_dir(config) / "daily_candidates.csv")
    scores = read_csv_if_exists(report_dir(config) / "daily_scores.csv")
    signals = read_csv_if_exists(report_dir(config) / "signals.csv")
    trades = read_csv_if_exists(report_dir(config) / "trade_detail.csv")
    market = read_csv_if_exists(report_dir(config) / "market_regime.csv")
    industry = read_csv_if_exists(report_dir(config) / "industry_regime.csv")
    theme = read_csv_if_exists(report_dir(config) / "theme_regime.csv")
    target_history = read_csv_if_exists(target_dir(config) / "target_history.csv")

    version_order = [item["version"] for item in config["ablations"]]
    summary["version_order"] = summary["version"].map({version: idx for idx, version in enumerate(version_order)})
    summary = summary.sort_values("version_order").drop(columns=["version_order"])
    best = summary.sort_values("total_return_with_cost", ascending=False).head(1)
    final = summary[summary["version"] == "layered_exit"]

    if not trades.empty and not universe.empty:
        trades = trades.merge(universe[["instrument", "name"]], on="instrument", how="left")
    if not trades.empty and not membership.empty:
        trades = trades.merge(
            membership[["instrument", "industry_name"]].drop_duplicates("instrument"),
            on="instrument",
            how="left",
        )

    generated_at = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    sources = sorted(set(membership_status.get("source", pd.Series(dtype=str)).dropna().astype(str)) - {""})
    mapped_count = (
        int(universe["instrument"].astype(str).isin(set(membership["instrument"].astype(str))).sum())
        if not universe.empty and not membership.empty
        else 0
    )
    target_successes = int((target_status.get("status", pd.Series(dtype=str)) != "failed").sum()) if not target_status.empty else 0
    target_failures = int((target_status.get("status", pd.Series(dtype=str)) == "failed").sum()) if not target_status.empty else 0

    lines = [
        "# Explore3 EMA Trend Rule Strategy Report",
        "",
        "## 1. Executive Summary",
        "",
        f"- Report generated: `{generated_at}` Asia/Shanghai.",
        f"- This is a rule-only Explore3 phase-one experiment. It does not use Alpha360, LightGBM, or any model predictions.",
        f"- Stock daily bars are read from `{config['paths']['provider_uri']}` and treated as read-only Explore1 cache input.",
        f"- The static stock universe is `{config['qlib']['market']}` with `{manifest.get('stock_cache_instruments', 'NA')}` resolved instruments.",
        f"- Backtest window is `{config['dates']['backtest_start']}` to `{config['dates']['backtest_end']}`; source data ends at `{config['dates']['data_end']}`.",
        f"- Final selected phase-one strategy is `layered_exit`; it produced `{format_pct(final['total_return_with_cost'].iloc[0]) if not final.empty else 'NA'}` cost-after return and `{format_pct(final['max_drawdown'].iloc[0]) if not final.empty else 'NA'}` max drawdown.",
        f"- The highest raw return variant is `{best['version'].iloc[0] if not best.empty else 'NA'}` with `{format_pct(best['total_return_with_cost'].iloc[0]) if not best.empty else 'NA'}` cost-after return.",
        f"- The main result is not that the layered version maximizes return. It reduces drawdown and raises trade quality relative to the broad EMA-state baseline.",
        "",
        "## 2. Reproduction Contract",
        "",
        "| Item | Value |",
        "| --- | --- |",
        f"| Config | `{relpath(config['_config_path'])}` |",
        f"| Config SHA256 | `{config['_config_hash']}` |",
        f"| CLI | `uv run python Explore3/scripts/run_explore3.py all --config Explore3/configs/trend_rule_v1.yaml` |",
        f"| Provider URI | `{config['paths']['provider_uri']}` |",
        f"| Market | `{config['qlib']['market']}` |",
        f"| Benchmark | `{config['qlib']['benchmark']}` |",
        f"| Frequency | `{config['costs']['freq']}` |",
        f"| Deal price | `{config['costs']['deal_price']}`; close-based signals are executed at next trading day open |",
        f"| Initial account | `{format_money(config['costs']['account'])}` |",
        f"| Open cost | `{format_pct(config['costs']['open_cost'])}` |",
        f"| Close cost | `{format_pct(config['costs']['close_cost'])}` |",
        f"| Min cost | `{format_money(config['costs']['min_cost'])}` |",
        f"| Limit threshold | `{format_pct(config['costs']['limit_threshold'])}` |",
        f"| Risk-unit sizing | `{config['rules']['portfolio'].get('risk_unit_sizing_enabled', False)}` |",
        f"| Tushare token stored in artifacts | `No`; manifest records only `tushare_token_present={manifest.get('tushare_token_present', False)}` |",
        "",
        "## 3. Data Sources And Coverage",
        "",
        "### 3.1 Stock Qlib Provider",
        "",
    ]
    if not data_quality.empty:
        total_missing = int(pd.to_numeric(data_quality["missing_values"], errors="coerce").sum())
        lines.extend(
            markdown_table(
                ["Check", "Value"],
                [
                    ["Instruments checked", format_int(len(data_quality))],
                    ["Failed instruments", format_int((data_quality["status"] == "failed").sum())],
                    ["Coverage start", safe_min(data_quality["start"])],
                    ["Coverage end", safe_max(data_quality["end"])],
                    ["Total provider rows", format_int(manifest.get("stock_cache_rows"))],
                    ["Total missing field values", format_int(total_missing)],
                    ["Duplicate date rows", format_int(pd.to_numeric(data_quality["duplicate_dates"], errors="coerce").sum())],
                    ["Required fields", ", ".join(config["qlib"]["required_fields"])],
                ],
            )
        )
        lines.extend(["", "Provider rows by instrument are available in `Explore3/outputs/reports/explore1_cache_coverage.csv`.", ""])
    lines.extend(["### 3.2 Market, Industry, And Theme Targets", ""])
    if not target_status.empty:
        target_rows = []
        for target_type, group in target_status.groupby("target_type", sort=False):
            target_rows.append(
                [
                    target_type,
                    format_int(len(group)),
                    format_int((group["status"] != "failed").sum()),
                    format_int((group["status"] == "failed").sum()),
                    format_int(pd.to_numeric(group["rows"], errors="coerce").sum()),
                    safe_min(group["start"]),
                    safe_max(group["end"]),
                    ", ".join(sorted(set(group["source"].dropna().astype(str)) - {""})),
                ]
            )
        lines.extend(markdown_table(["Type", "Targets", "Fetched", "Failed", "Rows", "Start", "End", "Sources"], target_rows))
        lines.extend(
            [
                "",
                f"- Total target history rows: `{format_int(len(target_history))}`.",
                f"- Target fetch successes: `{format_int(target_successes)}`; failures: `{format_int(target_failures)}`.",
                "- Market and theme index histories use `tushare.index_daily` when available.",
                "- SW2021 industry index histories use `tushare.sw_daily`.",
                "",
            ]
        )
    lines.extend(["### 3.3 SW2021 Industry Membership", ""])
    if not membership_status.empty:
        lines.extend(
            markdown_table(
                ["Metric", "Value"],
                [
                    ["Membership source", ", ".join(sources) if sources else "unavailable"],
                    ["Industry targets", format_int(len(membership_status))],
                    ["Failed industry memberships", format_int((membership_status["status"] == "failed").sum())],
                    ["Active constituent rows", format_int(len(membership))],
                    ["Universe instruments mapped", f"{format_int(mapped_count)} / {format_int(len(universe)) if not universe.empty else 'NA'}"],
                    ["Membership as-of date", safe_max(membership_status["source_trade_date"])],
                ],
            )
        )
        membership_rows = []
        for _, row in membership_status.sort_values("industry_ts_code").iterrows():
            membership_rows.append(
                [
                    row["industry_ts_code"],
                    row["industry_target_key"],
                    row["status"],
                    format_int(row["rows"]),
                    row.get("source", ""),
                    row.get("source_trade_date", ""),
                ]
            )
        lines.extend(["", "Detailed industry membership status:", ""])
        lines.extend(markdown_table(["Industry", "Target key", "Status", "Rows", "Source", "As-of"], membership_rows))
        lines.append("")

    lines.extend(
        [
            "## 4. Rule Design Implemented",
            "",
            "### 4.1 Strategy Layers",
            "",
            "1. Static large-cap mainboard stock universe copied from Explore1.",
            "2. Market regime filter from broad-market EMA60 state and slope.",
            "3. Market breadth filter from stock-pool EMA state ratios.",
            "4. SW2021 industry trend filter from industry index EMA60, slope, and 60-day relative return versus broad market.",
            "5. EMA trend candidate state on each stock.",
            "6. Cross-sectional `trend_score` ranking.",
            "7. Breakout and pullback entry triggers.",
            "8. ATR/structure stop and layered exit rules.",
            "",
            "### 4.2 Core Thresholds",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Rule", "Config value"],
            [
                ["Market trend", "broad_market close > EMA60 and EMA60 slope20 > 0"],
                ["Market breadth", f"close > EMA60 ratio > {format_pct(config['rules']['width']['close_gt_ema60'])}; EMA20 > EMA60 ratio > {format_pct(config['rules']['width']['ema20_gt_ema60'])}"],
                ["Candidate distance", f"dist_ema20 < min({format_pct(config['rules']['candidate']['max_dist_ema20'])}, {config['rules']['candidate']['atr_dist_multiplier']} * ATR20 / close)"],
                ["Candidate volatility", f"volatility20 <= daily p{int(config['rules']['candidate']['volatility_quantile'] * 100)}"],
                ["Candidate liquidity", f"avg_money20 >= daily p{int(config['rules']['candidate']['money_quantile'] * 100)}"],
                ["Trend-score buyable set", f"top {format_pct(config['rules']['score']['top_pct'])} by score among industry-filtered candidates"],
                ["Breakout", f"close > prior {config['rules']['breakout']['lookback']}D high, money_ratio20 >= {config['rules']['breakout']['money_ratio']}, close in upper half, upper shadow <= {format_pct(config['rules']['breakout']['upper_shadow_max'])}"],
                ["Pullback", f"pullback near EMA20/EMA30 within {format_pct(config['rules']['pullback']['ema_band_pct'])}, above EMA60, volume ratio <= 1.0, close reclaims EMA20"],
                ["Fixed stop", f"{format_pct(config['rules']['stops']['fixed_stop_pct'])} below entry"],
                ["ATR/structure stop", f"structure low minus {config['rules']['stops']['structure_atr_buffer']} * ATR20, fallback {config['rules']['stops']['atr_multiplier']} * ATR20"],
                ["Time stop", f"{config['rules']['stops']['time_stop_days']} calendar days without profit"],
                ["Max positions", str(config['rules']['portfolio']['max_positions'])],
                ["Single stock max weight", format_pct(config['rules']['portfolio']['single_stock_max_weight'])],
                ["Max daily new weight", format_pct(config['rules']['portfolio']['max_daily_new_weight'])],
            ],
        )
    )

    lines.extend(["", "### 4.3 Trend Score Formula", ""])
    score_rows = [[component, str(weight)] for component, weight in config["rules"]["score"]["weights"].items()]
    lines.extend(markdown_table(["Component", "Weight"], score_rows))
    lines.extend(
        [
            "",
            "All score components are winsorized by daily cross-section and converted to z-scores before weighting.",
            "",
            "### 4.4 `layered_exit` Strategy Mechanics: Entry, Holding, And Exit",
            "",
            "`layered_exit` 是本轮 Explore3 第一阶段的最终规则版本。它不是简单的 `EMA20 > EMA60` 买入策略，而是一个分层趋势交易状态机：先判断是否处在适合趋势交易的市场和行业环境，再判断个股是否处于趋势候选状态，再用 `trend_score` 排序，最后只在突破或回踩触发时买入。买入之后，是否继续持有不再要求每天重新满足入场条件，而是由结构止损、ATR trailing、时间止损和 EMA60 趋势终结线共同决定。",
            "",
            "#### 4.4.1 入场总流程",
            "",
            "信号日为 `T` 日。所有入场条件都使用 `T` 日收盘后可以观察到的数据；实际成交安排在 `T+1` 交易日开盘。若 `T+1` 开盘价触发主板近似涨停限制，即 `open >= prev_close * (1 + limit_threshold)`，买入会被跳过。",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Layer", "Required condition", "Purpose"],
            [
                ["股票池", f"`{config['qlib']['market']}` 静态大市值主板股票池", "降低小票、低流动性和非主板涨跌停规则带来的噪音"],
                ["市场趋势", "沪深300 `close > EMA60` 且 `EMA60 slope20 > 0`", "只在主市场趋势向上时开新仓"],
                ["市场宽度", f"股票池 `close > EMA60` 比例 > {format_pct(config['rules']['width']['close_gt_ema60'])}，且 `EMA20 > EMA60` 比例 > {format_pct(config['rules']['width']['ema20_gt_ema60'])}", "避免指数被少数权重股拉住但多数股票已经转弱"],
                ["行业顺风", "个股所属 SW2021 行业指数 `close > EMA60`、`EMA60 slope20 > 0`、`ret60 > broad_market ret60`", "只在行业趋势也顺风时交易个股"],
                ["个股趋势候选", "`EMA20 > EMA60`、`EMA60 slope10 > 0`、`close > EMA60`", "EMA 多头排列只表示候选状态，不直接等于买入"],
                ["不追高", f"`dist_ema20 < min({format_pct(config['rules']['candidate']['max_dist_ema20'])}, {config['rules']['candidate']['atr_dist_multiplier']} * ATR20 / close)`", "避免在短期加速末端追入"],
                ["波动过滤", f"`volatility20 <= daily p{int(config['rules']['candidate']['volatility_quantile'] * 100)}`", "排除波动过高、止损距离不稳定的候选"],
                ["流动性过滤", f"`avg_money20 >= daily p{int(config['rules']['candidate']['money_quantile'] * 100)}`", "排除当日截面中成交额偏低的股票"],
                ["趋势质量", f"`trend_score_pct <= {format_pct(config['rules']['score']['top_pct'])}`", "只保留行业过滤后趋势质量排名靠前的候选"],
                ["最终触发", "`breakout_entry OR pullback_entry`", "必须有明确买点，不能只因 EMA 多头就买"],
            ],
        )
    )
    lines.extend(
        [
            "",
            "#### 4.4.2 突破型入场",
            "",
            "突破型入场用于捕捉趋势继续向上加速。该类信号必须先通过所有共同过滤，再满足以下触发条件：",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Condition", "Value"],
            [
                ["突破位置", f"`close > prior {config['rules']['breakout']['lookback']}D high`"],
                ["成交额确认", f"`money_ratio20 >= {config['rules']['breakout']['money_ratio']}`"],
                ["日内收盘位置", "`close_pos >= 0.5`，即收盘在当日振幅上半区"],
                ["上影线控制", f"`upper_shadow_pct <= {format_pct(config['rules']['breakout']['upper_shadow_max'])}`"],
                ["追高控制", "仍需满足 `dist_ema20 < max_dist`"],
                ["成交方式", "`T` 日收盘生成信号，`T+1` 日开盘买入"],
            ],
        )
    )
    lines.extend(
        [
            "",
            "#### 4.4.3 回踩型入场",
            "",
            "回踩型入场用于捕捉趋势中的缩量回调后重新转强。该类信号必须先通过所有共同过滤，再满足以下触发条件：",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Condition", "Value"],
            [
                ["回踩位置", f"`low <= EMA20 * (1 + {format_pct(config['rules']['pullback']['ema_band_pct'])})` 或 `low <= EMA30 * (1 + {format_pct(config['rules']['pullback']['ema_band_pct'])})`"],
                ["趋势底线", "`low > EMA60`，回踩不能跌破中期趋势线"],
                ["缩量回调", "`money_ratio20 <= 1.0`"],
                ["重新转强", "`close >= EMA20` 且 `close > open`"],
                ["成交方式", "`T` 日收盘生成信号，`T+1` 日开盘买入"],
            ],
        )
    )
    lines.extend(
        [
            "",
            "如果同一天同时满足突破和回踩，代码优先把交易标记为 `breakout`；否则满足回踩条件时标记为 `pullback`。",
            "",
            "#### 4.4.4 建仓和初始风险",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Item", "Rule"],
            [
                ["最大持仓数", str(config["rules"]["portfolio"]["max_positions"])],
                ["单票目标权重", f"`min({format_pct(config['rules']['portfolio']['single_stock_max_weight'])}, risk_degree / max_positions)`，当前约为 `4.75%`"],
                ["单日新增仓位上限", format_pct(config["rules"]["portfolio"]["max_daily_new_weight"])],
                ["成交股数", "按 100 股整数手向下取整"],
                ["买入成本", f"`max(value * {config['costs']['open_cost']}, {config['costs']['min_cost']})`"],
                ["初始风险 R", "`R = max(entry_price - initial_stop, entry_price * 1%)`"],
            ],
        )
    )
    lines.extend(
        [
            "",
            "初始止损按入场类型决定：",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Entry type", "Initial stop"],
            [
                ["breakout", f"`rolling_low20 - {config['rules']['stops']['structure_atr_buffer']} * ATR20`"],
                ["pullback", f"`recent_low5 - {config['rules']['stops']['structure_atr_buffer']} * ATR20`"],
                ["fallback", f"若结构止损无效，使用 `entry_price - {config['rules']['stops']['atr_multiplier']} * ATR20`"],
            ],
        )
    )
    lines.extend(
        [
            "",
            "#### 4.4.5 持有条件",
            "",
            "买入后，持仓不会因为市场过滤、行业过滤或入场触发条件消失而立刻卖出。换句话说，入场条件只决定能不能开仓；开仓后，是否继续持有由持仓风控状态决定。",
            "",
            "每天收盘后，策略根据当前浮盈对应的 `R` 值更新 `current_stop`。`current_stop` 只会上移，不会下移。",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Holding state", "Stop update"],
            [
                ["盈利未达到 1R", "`current_stop` 保持为初始结构/ATR 止损"],
                ["盈利达到 1R", "`current_stop = max(current_stop, entry_price)`，把止损抬到成本附近"],
                ["盈利达到 2R", f"`current_stop = max(current_stop, EMA20, close - {config['rules']['stops']['trailing_atr_multiplier']} * ATR20)`"],
                ["盈利达到 3R 且价格明显远离 EMA20", "若 `dist_ema20 > 10%`，则 `current_stop` 至少抬到 `EMA20`"],
            ],
        )
    )
    lines.extend(
        [
            "",
            "#### 4.4.6 退出条件",
            "",
            "退出信号同样在 `T` 日收盘后判断，实际卖出安排在 `T+1` 交易日开盘。若 `T+1` 开盘价触发近似跌停限制，即 `open <= prev_close * (1 - limit_threshold)`，该卖出订单会被跳过，等待后续日期重新触发。",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Priority", "Exit reason", "Condition", "Meaning"],
            [
                ["1", "`stop_loss` or `trailing_stop`", "`close <= current_stop`", "先执行硬风控；若 `current_stop >= entry_price`，记为 `trailing_stop`，否则记为 `stop_loss`"],
                ["2", "`time_stop`", f"`holding_days >= {config['rules']['stops']['time_stop_days']}` 且 `close <= entry_price`", "买入后一段时间仍不赚钱，则释放资金"],
                ["3", "`ema60_exit`", "`close < EMA60`", "中期趋势破坏，退出剩余趋势仓位"],
                ["4", "`end_of_backtest`", "回测结束后第一个交易日开盘强制平仓", "只用于结算回测期末仍持有的仓位"],
            ],
        )
    )
    if not final.empty:
        lines.extend(
            [
                "",
                "#### 4.4.7 本次回测中的实际表现",
                "",
                f"`layered_exit` 共完成 `{format_int(final['trades'].iloc[0])}` 笔交易，其中突破型 `{format_int(final['breakout_trades'].iloc[0])}` 笔，回踩型 `{format_int(final['pullback_trades'].iloc[0])}` 笔；胜率 `{format_pct(final['win_rate'].iloc[0])}`，成本后收益 `{format_pct(final['total_return_with_cost'].iloc[0])}`，最大回撤 `{format_pct(final['max_drawdown'].iloc[0])}`。",
                "",
                "本版本的设计目标不是追求最高单次收益，而是用分层退出减少趋势利润回吐和组合回撤。和 `ema_state_only` 相比，它牺牲了一部分总收益，但把最大回撤从 `-21.04%` 降到 `-8.63%`。",
                "",
            ]
        )
    lines.extend(
        [
            "## 5. Candidate Funnel And Regime Diagnostics",
            "",
        ]
    )
    if not candidates.empty:
        funnel_cols = [
            "ema_state",
            "market_ok_entry",
            "width_ok_entry",
            "industry_ok_entry",
            "trend_score_top20_entry",
            "breakout_entry",
            "pullback_entry",
            "combined_entry",
        ]
        funnel_rows = []
        for col in funnel_cols:
            count = pd.to_numeric(candidates[col], errors="coerce")
            funnel_rows.append(
                [
                    col,
                    format_number(count.mean(), 2),
                    format_int(count.median()),
                    format_int(count.max()),
                    format_int((count > 0).sum()),
                ]
            )
        lines.extend(markdown_table(["Stage", "Avg daily count", "Median", "Max", "Days active"], funnel_rows))
        lines.extend(
            [
                "",
                f"- Candidate table rows: `{format_int(len(candidates))}` trading days.",
                f"- Score table rows: `{format_int(len(scores))}` stock-day candidate rows.",
                f"- Signal table rows: `{format_int(len(signals))}` stock-day signal rows.",
                "",
            ]
        )
    if not market.empty:
        broad = market[market["target_key"] == "broad_market"].copy()
        lines.extend(["### 5.1 Market And Breadth State", ""])
        if not broad.empty:
            lines.extend(
                markdown_table(
                    ["Metric", "Value"],
                    [
                        ["Broad-market trend-ok days", format_int(broad["trend_ok"].sum())],
                        ["Broad-market trend-ok ratio", format_pct(broad["trend_ok"].mean())],
                        ["Width-ok days", format_int(broad["width_ok"].sum())],
                        ["Width-ok ratio", format_pct(broad["width_ok"].mean())],
                        ["Average close > EMA60 breadth", format_pct(broad["close_gt_ema60_ratio"].mean())],
                        ["Average EMA20 > EMA60 breadth", format_pct(broad["ema20_gt_ema60_ratio"].mean())],
                    ],
                )
            )
        market_rows = []
        for _, row in market.groupby(["target_key", "target_name"], sort=False).agg(
            days=("date", "count"),
            trend_ok_ratio=("trend_ok", "mean"),
            avg_ret60=("ret60", "mean"),
            source=("source", "first"),
        ).reset_index().iterrows():
            market_rows.append(
                [row["target_key"], row["target_name"], format_int(row["days"]), format_pct(row["trend_ok_ratio"]), format_pct(row["avg_ret60"]), row["source"]]
            )
        lines.extend(["", "Market target regime summary:", ""])
        lines.extend(markdown_table(["Target", "Name", "Days", "Trend-ok ratio", "Avg ret60", "Source"], market_rows))
        lines.append("")
    if not industry.empty:
        industry_summary = industry.groupby(["target_key", "target_name"], sort=False).agg(
            days=("date", "count"),
            trend_ok_ratio=("industry_trend_ok", "mean"),
            avg_ret60=("ret60", "mean"),
        ).reset_index()
        top_ind = industry_summary.sort_values("trend_ok_ratio", ascending=False).head(8)
        low_ind = industry_summary.sort_values("trend_ok_ratio", ascending=True).head(8)
        lines.extend(["### 5.2 Industry Regime Extremes", ""])
        lines.extend(markdown_table(["Target", "Industry", "Days", "Trend-ok ratio", "Avg ret60"], [
            [row["target_key"], row["target_name"], format_int(row["days"]), format_pct(row["trend_ok_ratio"]), format_pct(row["avg_ret60"])]
            for _, row in top_ind.iterrows()
        ]))
        lines.extend(["", "Lowest industry trend-ok ratios:", ""])
        lines.extend(markdown_table(["Target", "Industry", "Days", "Trend-ok ratio", "Avg ret60"], [
            [row["target_key"], row["target_name"], format_int(row["days"]), format_pct(row["trend_ok_ratio"]), format_pct(row["avg_ret60"])]
            for _, row in low_ind.iterrows()
        ]))
        lines.append("")
    if not theme.empty:
        theme_rows = []
        for _, row in theme.groupby(["target_key", "target_name"], sort=False).agg(
            days=("date", "count"),
            trend_ok_ratio=("theme_trend_ok", "mean"),
            avg_ret60=("ret60", "mean"),
            source=("source", "first"),
        ).reset_index().iterrows():
            theme_rows.append([row["target_key"], row["target_name"], format_int(row["days"]), format_pct(row["trend_ok_ratio"]), format_pct(row["avg_ret60"]), row["source"]])
        lines.extend(["### 5.3 Theme State", ""])
        lines.append("Theme state is recorded for style diagnostics only. It is not used as a hard stock membership filter in phase one.")
        lines.extend(["", *markdown_table(["Theme", "Name", "Days", "Trend-ok ratio", "Avg ret60", "Source"], theme_rows), ""])

    lines.extend(
        [
            "## 6. Ablation Results",
            "",
            "### 6.1 Main Ablation Table",
            "",
        ]
    )
    table_rows = []
    for _, row in summary.iterrows():
        table_rows.append(
            [
                row["version"],
                format_int(row.get("trades")),
                format_pct(row.get("win_rate")),
                format_pct(row.get("total_return_with_cost")),
                format_pct(row.get("total_return_without_cost")),
                format_pct(row.get("annual_return_with_cost")),
                format_pct(row.get("max_drawdown")),
                format_number(row.get("return_drawdown_ratio"), 2),
                format_number(row.get("turnover_mean"), 4),
                format_money(row.get("ending_account")),
            ]
        )
    lines.extend(
        markdown_table(
            [
                "Version",
                "Trades",
                "Win rate",
                "Return after cost",
                "Return before cost",
                "Annual after cost",
                "Max drawdown",
                "Ret/DD",
                "Avg turnover",
                "Ending account",
            ],
            table_rows,
        )
    )
    lines.extend(["", "### 6.2 Incremental Interpretation", ""])
    delta_rows = []
    prev = None
    for _, row in summary.iterrows():
        if prev is None:
            delta_rows.append([row["version"], "baseline", "NA", "NA", "NA"])
        else:
            delta_rows.append(
                [
                    row["version"],
                    f"after {prev['version']}",
                    format_pct(row["total_return_with_cost"] - prev["total_return_with_cost"]),
                    format_pct(row["max_drawdown"] - prev["max_drawdown"]),
                    format_int(row["trades"] - prev["trades"]),
                ]
            )
        prev = row
    lines.extend(markdown_table(["Version", "Comparison", "Return delta", "Drawdown delta", "Trade delta"], delta_rows))
    lines.append("")

    lines.extend(["### 6.3 Annual / Partial-Year Performance", ""])
    year_rows = portfolio_year_rows(config, summary["version"].tolist())
    lines.extend(markdown_table(["Version", "Year", "Return", "Max drawdown", "Avg turnover", "Cost sum", "Ending account"], year_rows))

    lines.extend(["", "## 7. Trade Diagnostics", ""])
    if not trades.empty:
        lines.extend(["### 7.1 Entry-Type Statistics", ""])
        entry_rows = summarize_trade_group(trades, ["version", "entry_type"])
        lines.extend(markdown_table(["Version", "Entry type", "Trades", "Win rate", "Avg net return", "Avg gross return", "Avg holding days", "Sum net return"], entry_rows))
        lines.extend(["", "### 7.2 Exit Reason Statistics", ""])
        exit_rows = summarize_trade_group(trades, ["version", "exit_reason"])
        lines.extend(markdown_table(["Version", "Exit reason", "Trades", "Win rate", "Avg net return", "Avg gross return", "Avg holding days", "Sum net return"], exit_rows))
        layered = trades[trades["version"] == "layered_exit"].copy()
        if not layered.empty:
            lines.extend(["", "### 7.3 Layered Strategy Trade Detail", ""])
            layer_rows = summarize_trade_group(layered, ["entry_type"])
            lines.extend(markdown_table(["Entry type", "Trades", "Win rate", "Avg net return", "Avg gross return", "Avg holding days", "Sum net return"], layer_rows))
            top_inst = (
                layered.groupby(["instrument", "name", "industry_name"], dropna=False)
                .agg(
                    trades=("instrument", "count"),
                    win_rate=("cost_after_return", lambda s: (pd.to_numeric(s, errors="coerce") > 0).mean()),
                    avg_return=("cost_after_return", "mean"),
                    sum_return=("cost_after_return", "sum"),
                    avg_holding=("holding_days", "mean"),
                )
                .reset_index()
                .sort_values("sum_return", ascending=False)
                .head(15)
            )
            lines.extend(["", "Top layered-exit instruments by summed net trade return:", ""])
            lines.extend(
                markdown_table(
                    ["Instrument", "Name", "Industry", "Trades", "Win rate", "Avg net", "Sum net", "Avg holding"],
                    [
                        [
                            row["instrument"],
                            row["name"] if pd.notna(row["name"]) else "",
                            row["industry_name"] if pd.notna(row["industry_name"]) else "",
                            format_int(row["trades"]),
                            format_pct(row["win_rate"]),
                            format_pct(row["avg_return"]),
                            format_pct(row["sum_return"]),
                            format_number(row["avg_holding"], 1),
                        ]
                        for _, row in top_inst.iterrows()
                    ],
                )
            )
            top_exit = layered["exit_reason"].value_counts().reset_index()
            lines.extend(["", "Layered-exit exit reason counts:", ""])
            lines.extend(markdown_table(["Exit reason", "Count"], [[row["exit_reason"], format_int(row["count"])] for _, row in top_exit.iterrows()]))
        lines.append("")

    lines.extend(["## 8. Core Findings", ""])
    if not best.empty:
        row = best.iloc[0]
        lines.append(
            f"- Best cost-after version by total return: `{row['version']}` "
            f"with `{format_pct(row['total_return_with_cost'])}`."
        )
    if not final.empty:
        row = final.iloc[0]
        lines.append(
            f"- Final layered strategy cost-after return: `{format_pct(row['total_return_with_cost'])}`, "
            f"max drawdown: `{format_pct(row['max_drawdown'])}`, trades: `{int(row['trades'])}`."
        )
        lines.append(
            f"- Breakout trades: `{int(row.get('breakout_trades', 0))}`, "
            f"pullback trades: `{int(row.get('pullback_trades', 0))}`."
        )
        lines.append(
            "- Cost-after returns remain positive in the tested variants, but the highest-return baseline also has "
            "the largest drawdown; the layered version mainly improves drawdown and trade quality, not raw return."
        )
        lines.append(
            "- Meta-labeling is worth a later Explore3 phase only after validating that the lower-drawdown rule "
            "variants remain stable under fresh dates or stricter train/valid parameter selection."
        )
    lines.extend(
        [
            "",
            "## 9. Bias, Caveats, And What Needs Attention",
            "",
            "- Phase one uses the Explore1 static large-cap mainboard universe. This accepts survivor bias and future-function risk for workflow and rule-structure validation.",
            "- The static universe is not point-in-time. It should not be interpreted as an investable historical universe without additional survivorship-bias controls.",
            "- Target histories and SW2021 membership are cached under Explore3. Stock daily bars are not refetched or backfilled in Explore3.",
            "- SW2021 membership uses active `tushare.index_member` rows because `tushare.index_weight` returned empty for SW industry indexes in this environment.",
            "- Theme state is reported as an index-level style regime only; it is not a stock membership filter.",
            "- Market, industry, and theme target lists are fixed by `requirement.md`; the implementation does not auto-extend them.",
            "- The backtest engine is a deterministic pandas state machine backed by Qlib data. It is not Qlib `TopkDropoutStrategy`, because this experiment requires trade-level stop, R, entry type, and exit-reason accounting.",
            "- Costs are constant approximations across the whole backtest period. A production-grade study should use date-aware fees and tax assumptions.",
            "- Limit handling uses a mainboard-style `limit_threshold=0.095`; this is acceptable only because the Explore1 universe is intended to be mainboard A shares.",
            "- Results should be treated as exploratory if rules are changed after inspecting the 2025-2026 test window.",
            "",
            "## 10. Files Produced",
            "",
        ]
    )
    artifact_rows = []
    for path in manifest.get("output_paths", []):
        target = topic_path(path)
        artifact_rows.append([f"`{path}`", "yes" if target.exists() else "missing", format_int(target.stat().st_size) if target.exists() else "NA"])
    lines.extend(markdown_table(["Path", "Exists", "Bytes"], artifact_rows))
    lines.extend(
        [
            "",
            "## 11. Next-Step Recommendation",
            "",
            "- Do not move directly to a large model search from this result alone.",
            "- First rerun the same pipeline after adding fresh dates, then compare whether lower drawdown from `layered_exit` survives.",
            "- If the result is stable, the natural next extension is meta-labeling on EMA candidates: predict whether a candidate has enough forward R-adjusted payoff to justify the trade.",
            "- If the result is not stable, focus on parameter discipline and point-in-time universe/industry membership before adding models.",
            "",
        ]
    )
    report_path = ensure_parent(report_dir(config) / "explore3_report.md")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    legacy_report_path = ensure_parent(EXPLORE_DIR / "reports" / "explore3_report.md")
    legacy_report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    outputs = [report_path, legacy_report_path]
    record_manifest(config, "report", outputs, {"report_path": relpath(report_path)})
    print(f"wrote {relpath(report_path)}", flush=True)
    return outputs


def command_all(config: dict[str, Any]) -> list[Path]:
    outputs: list[Path] = []
    outputs.extend(command_prepare_universe(config))
    outputs.extend(command_fetch_targets(config))
    outputs.extend(command_validate_cache(config))
    outputs.extend(command_build_regimes(config))
    outputs.extend(command_build_signals(config))
    outputs.extend(command_run_ablation(config))
    outputs.extend(command_report(config))
    record_manifest(config, "all", outputs)
    return outputs


def command_self_test() -> None:
    dates = [pd.Timestamp("2025-01-02"), pd.Timestamp("2025-01-03")]
    assert next_trading_date(dates, 0) == pd.Timestamp("2025-01-03")
    assert next_trading_date(dates, 1) is None
    row = pd.Series({"prev_close_for_limit": 10.0, "open": 11.0})
    assert is_limit_blocked(row, "buy", 0.095)
    row = pd.Series({"prev_close_for_limit": 10.0, "open": 8.9})
    assert is_limit_blocked(row, "sell", 0.095)
    gross, net = trade_return(10.0, 11.0, 5.0, 5.0, 100.0)
    assert gross > 0
    assert net > 0
    print("self-test passed", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Explore3 EMA trend rule workflow.")
    parser.add_argument(
        "command",
        choices=[
            "prepare-universe",
            "fetch-targets",
            "validate-cache",
            "build-regimes",
            "build-signals",
            "run-ablation",
            "report",
            "all",
            "self-test",
        ],
    )
    parser.add_argument("--config", default="Explore3/configs/trend_rule_v1.yaml")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "self-test":
        command_self_test()
        return 0
    config = load_config(args.config)
    try:
        if args.command == "prepare-universe":
            command_prepare_universe(config)
        elif args.command == "fetch-targets":
            command_fetch_targets(config)
        elif args.command == "validate-cache":
            command_validate_cache(config)
        elif args.command == "build-regimes":
            command_build_regimes(config)
        elif args.command == "build-signals":
            command_build_signals(config)
        elif args.command == "run-ablation":
            command_run_ablation(config)
        elif args.command == "report":
            command_report(config)
        elif args.command == "all":
            command_all(config)
        else:
            raise ValueError(args.command)
        return 0
    except Exception as exc:  # noqa: BLE001
        error_path = report_dir(config) / "last_error.json"
        write_json(
            {
                "command": args.command,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
            error_path,
        )
        print(f"ERROR: {exc}", file=sys.stderr)
        print(f"wrote {relpath(error_path)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
