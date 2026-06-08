from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd


PROXY_ENV_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy")

MAIN_BOARD_PREFIXES = ("000", "001", "002", "003", "600", "601", "603", "605")
CHINEXT_PREFIXES = ("300", "301")
EXCLUDED_PREFIXES = ("688", "689")

DAILY_RENAME = {
    "日期": "date",
    "股票代码": "code",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "money",
    "换手率": "turnover_rate",
    "date": "date",
    "open": "open",
    "close": "close",
    "high": "high",
    "low": "low",
    "volume": "volume",
    "amount": "money",
    "turnover": "turnover_rate",
}

QLIB_COLUMNS = [
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "money",
    "turnover_rate",
    "factor",
]


class DataSourceUnsupported(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class SourceAuditRow:
    category: str
    support_state: str
    function_name: str
    source_columns: tuple[str, ...] = ()
    units: str = ""
    source_date_field: str = ""
    historical: bool = False
    latest_only: bool = False
    fallback_state: str = ""
    sample_rows: int | None = None
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "support_state": self.support_state,
            "function_name": self.function_name,
            "source_columns": "|".join(self.source_columns),
            "units": self.units,
            "source_date_field": self.source_date_field,
            "historical": self.historical,
            "latest_only": self.latest_only,
            "fallback_state": self.fallback_state,
            "sample_rows": self.sample_rows,
            "notes": self.notes,
        }


def parse_date(value: str | date | pd.Timestamp) -> pd.Timestamp:
    if isinstance(value, pd.Timestamp):
        return value.normalize()
    if isinstance(value, date):
        return pd.Timestamp(value).normalize()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return pd.Timestamp(datetime.strptime(text, fmt)).normalize()
        except ValueError:
            pass
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"Invalid date {value!r}")
    return pd.Timestamp(parsed).normalize()


def ak_date(value: str | date | pd.Timestamp) -> str:
    return parse_date(value).strftime("%Y%m%d")


def qlib_date(value: str | date | pd.Timestamp) -> str:
    return parse_date(value).strftime("%Y-%m-%d")


def strip_code(value: str) -> str:
    text = str(value).strip().upper()
    if text.startswith(("SH", "SZ", "BJ")):
        text = text[2:]
    if "." in text:
        left, right = text.split(".", 1)
        text = right if left in {"SH", "SZ", "BJ"} else left
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        raise ValueError(f"No stock code found in {value!r}")
    return digits.zfill(6)


def exchange_from_code(code_or_instrument: str) -> str:
    code = strip_code(code_or_instrument)
    if code.startswith(("0", "2", "3")):
        return "SZ"
    if code.startswith(("5", "6", "9")):
        return "SH"
    if code.startswith(("4", "8")):
        return "BJ"
    raise ValueError(f"Cannot infer exchange from {code_or_instrument!r}")


def instrument_from_code(code_or_instrument: str) -> str:
    code = strip_code(code_or_instrument)
    return f"{exchange_from_code(code)}{code}"


def akshare_symbol_with_exchange_suffix(code_or_instrument: str) -> str:
    code = strip_code(code_or_instrument)
    return f"{code}.{exchange_from_code(code)}"


def akshare_symbol_with_market_prefix(code_or_instrument: str) -> str:
    code = strip_code(code_or_instrument)
    return f"{exchange_from_code(code).lower()}{code}"


def board_bucket(code_or_instrument: str) -> str | None:
    code = strip_code(code_or_instrument)
    if code.startswith(EXCLUDED_PREFIXES):
        return None
    if code.startswith(MAIN_BOARD_PREFIXES):
        return "main_board"
    if code.startswith(CHINEXT_PREFIXES):
        return "chinext"
    return None


def market_cap_threshold_cny(bucket: str) -> int:
    if bucket == "main_board":
        return 50_000_000_000
    if bucket == "chinext":
        return 20_000_000_000
    raise ValueError(f"Unsupported board bucket {bucket!r}")


def numeric_series(values: pd.Series) -> pd.Series:
    text = values.astype("string").str.replace(",", "", regex=False)
    text = text.str.replace("%", "", regex=False).str.strip()
    return pd.to_numeric(text, errors="coerce")


def normalize_daily_bars(
    df: pd.DataFrame,
    *,
    instrument: str,
    source_function: str,
    volume_unit: str,
    turnover_unit: str,
) -> pd.DataFrame:
    renamed = df.rename(columns=DAILY_RENAME).copy()
    required = {"date", "open", "high", "low", "close", "volume"}
    missing = required.difference(renamed.columns)
    if missing:
        raise ValueError(f"{source_function} missing daily columns: {sorted(missing)}")

    if "money" not in renamed.columns:
        renamed["money"] = np.nan
    if "turnover_rate" not in renamed.columns:
        renamed["turnover_rate"] = np.nan

    out = renamed[
        ["date", "open", "high", "low", "close", "volume", "money", "turnover_rate"]
    ].copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    for column in ["open", "high", "low", "close", "volume", "money", "turnover_rate"]:
        out[column] = numeric_series(out[column])

    if volume_unit == "hands":
        out["volume"] = out["volume"] * 100.0
    elif volume_unit != "shares":
        raise ValueError(f"Unsupported volume unit {volume_unit!r}")

    if turnover_unit == "percent":
        out["turnover_rate"] = out["turnover_rate"] / 100.0
    elif turnover_unit not in {"ratio", "unknown"}:
        raise ValueError(f"Unsupported turnover unit {turnover_unit!r}")

    out["instrument"] = instrument_from_code(instrument)
    out["source_function"] = source_function
    out["source_volume_unit"] = volume_unit
    out["source_turnover_unit"] = turnover_unit
    out = out.dropna(subset=["date", "open", "high", "low", "close", "volume"])
    out = out.drop_duplicates("date", keep="last").sort_values("date")
    return out.reset_index(drop=True)


def build_qlib_daily(raw: pd.DataFrame, qfq: pd.DataFrame) -> pd.DataFrame:
    raw_keep = raw[
        [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "money",
            "turnover_rate",
            "instrument",
        ]
    ].rename(
        columns={
            "open": "raw_open",
            "high": "raw_high",
            "low": "raw_low",
            "close": "raw_close",
            "volume": "raw_volume",
            "money": "raw_money",
        }
    )
    qfq_keep = qfq[["date", "open", "high", "low", "close", "instrument"]].copy()
    merged = qfq_keep.merge(raw_keep, on=["date", "instrument"], how="inner")
    merged["factor"] = np.where(
        merged["raw_close"] > 0, merged["close"] / merged["raw_close"], np.nan
    )
    merged["volume"] = merged["raw_volume"]
    merged["money"] = merged["raw_money"]
    merged = merged.replace([np.inf, -np.inf], np.nan)
    validate_qlib_daily(merged)
    return merged[
        QLIB_COLUMNS
        + [
            "instrument",
            "raw_open",
            "raw_high",
            "raw_low",
            "raw_close",
            "raw_volume",
            "raw_money",
        ]
    ].reset_index(drop=True)


def validate_qlib_daily(df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError("Qlib daily frame is empty")
    if df["date"].duplicated().any():
        raise ValueError("Duplicate trade dates in Qlib daily frame")
    for column in ["open", "high", "low", "close", "volume", "factor"]:
        if column not in df.columns:
            raise ValueError(f"Missing Qlib field {column}")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("QFQ OHLC contains non-positive values")
    if (df["volume"] < 0).any():
        raise ValueError("Volume contains negative values")
    if "money" in df.columns and (df["money"].dropna() < 0).any():
        raise ValueError("Money contains negative values")
    high_floor = df[["open", "low", "close"]].max(axis=1)
    low_ceiling = df[["open", "high", "close"]].min(axis=1)
    if (df["high"] < high_floor).any():
        raise ValueError("High is below open/low/close")
    if (df["low"] > low_ceiling).any():
        raise ValueError("Low is above open/high/close")
    if (df["factor"] <= 0).any():
        raise ValueError("Adjustment factor contains non-positive values")


def normalize_share_history(df: pd.DataFrame, *, source_function: str) -> pd.DataFrame:
    rename = {
        "变更日期": "share_date",
        "总股本": "total_share_asof",
        "已上市流通A股": "float_share_asof",
        "已流通股份": "listed_float_share_asof",
    }
    renamed = df.rename(columns=rename).copy()
    missing = {"share_date", "total_share_asof"}.difference(renamed.columns)
    if missing:
        raise ValueError(f"{source_function} missing share columns: {sorted(missing)}")
    out = renamed[[col for col in rename.values() if col in renamed.columns]].copy()
    out["share_date"] = pd.to_datetime(out["share_date"], errors="coerce")
    for column in out.columns:
        if column != "share_date":
            out[column] = numeric_series(out[column])
    out = out.dropna(subset=["share_date", "total_share_asof"])
    out = out.drop_duplicates("share_date", keep="last").sort_values("share_date")
    out["share_source"] = source_function
    return out.reset_index(drop=True)


def expand_share_asof(share_history: pd.DataFrame, calendar: Iterable[str]) -> pd.DataFrame:
    calendar_df = pd.DataFrame({"date": pd.to_datetime(list(calendar))}).sort_values("date")
    shares = share_history.sort_values("share_date")
    expanded = pd.merge_asof(
        calendar_df,
        shares,
        left_on="date",
        right_on="share_date",
        direction="backward",
    )
    expanded["date"] = expanded["date"].dt.strftime("%Y-%m-%d")
    expanded["share_source_date"] = expanded["share_date"].dt.strftime("%Y-%m-%d")
    expanded = expanded.drop(columns=["share_date"])
    return expanded


def resolve_trade_calendar(
    calendar: Iterable[str | date | pd.Timestamp],
    requested_start: str | date,
    requested_end: str | date,
) -> list[str]:
    start = parse_date(requested_start)
    end = parse_date(requested_end)
    dates = sorted({parse_date(value) for value in calendar})
    resolved = [value.strftime("%Y-%m-%d") for value in dates if start <= value <= end]
    if not resolved:
        raise ValueError(f"No trading sessions between {start.date()} and {end.date()}")
    return resolved


def next_trade_date_map(calendar: Iterable[str]) -> dict[str, str | None]:
    sessions = list(calendar)
    mapping: dict[str, str | None] = {}
    for idx, session in enumerate(sessions):
        mapping[session] = sessions[idx + 1] if idx + 1 < len(sessions) else None
    return mapping


def shift_membership_to_executable(raw_membership: pd.DataFrame, calendar: Iterable[str]) -> pd.DataFrame:
    required = {"membership_date", "instrument"}
    missing = required.difference(raw_membership.columns)
    if missing:
        raise ValueError(f"Raw membership missing columns: {sorted(missing)}")
    mapping = next_trade_date_map(calendar)
    shifted = raw_membership.copy()
    shifted["membership_date"] = pd.to_datetime(
        shifted["membership_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    shifted["usable_trade_date"] = shifted["membership_date"].map(mapping)
    shifted = shifted.dropna(subset=["usable_trade_date"]).copy()
    if shifted.duplicated(["usable_trade_date", "instrument"]).any():
        raise ValueError("Duplicate executable membership rows")
    return shifted.reset_index(drop=True)


def compress_executable_intervals(executable: pd.DataFrame, calendar: Iterable[str]) -> pd.DataFrame:
    required = {"usable_trade_date", "instrument"}
    missing = required.difference(executable.columns)
    if missing:
        raise ValueError(f"Executable membership missing columns: {sorted(missing)}")

    rank = {session: idx for idx, session in enumerate(calendar)}
    rows: list[dict[str, Any]] = []
    dates = executable[["instrument", "usable_trade_date"]].copy()
    dates["usable_trade_date"] = pd.to_datetime(
        dates["usable_trade_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    dates["calendar_rank"] = dates["usable_trade_date"].map(rank)
    if dates["calendar_rank"].isna().any():
        missing_dates = sorted(dates.loc[dates["calendar_rank"].isna(), "usable_trade_date"].unique())
        raise ValueError(f"Executable dates outside calendar: {missing_dates[:5]}")

    for instrument, group in dates.sort_values(["instrument", "calendar_rank"]).groupby("instrument"):
        group = group.drop_duplicates("usable_trade_date").reset_index(drop=True)
        start_date = group.loc[0, "usable_trade_date"]
        previous_date = start_date
        previous_rank = int(group.loc[0, "calendar_rank"])
        count = 1
        for row in group.iloc[1:].itertuples(index=False):
            current_rank = int(row.calendar_rank)
            current_date = row.usable_trade_date
            if current_rank == previous_rank + 1:
                previous_date = current_date
                previous_rank = current_rank
                count += 1
                continue
            rows.append(
                {
                    "instrument": instrument,
                    "start_datetime": start_date,
                    "end_datetime": previous_date,
                    "session_count": count,
                }
            )
            start_date = current_date
            previous_date = current_date
            previous_rank = current_rank
            count = 1
        rows.append(
            {
                "instrument": instrument,
                "start_datetime": start_date,
                "end_datetime": previous_date,
                "session_count": count,
            }
        )
    return pd.DataFrame(rows)


def write_qlib_instrument_intervals(intervals: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in intervals.sort_values(["instrument", "start_datetime"]).itertuples(index=False):
            handle.write(f"{row.instrument}\t{row.start_datetime}\t{row.end_datetime}\n")


@contextmanager
def without_proxy_env() -> Iterable[None]:
    old_values = {key: os.environ.get(key) for key in PROXY_ENV_KEYS}
    try:
        for key in PROXY_ENV_KEYS:
            os.environ.pop(key, None)
        yield
    finally:
        for key, value in old_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def is_proxy_error(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return "proxy" in text


def call_akshare(
    func: Callable[..., pd.DataFrame],
    *,
    retry_without_proxy: bool,
    **kwargs: Any,
) -> pd.DataFrame:
    try:
        return func(**kwargs)
    except Exception as exc:
        if retry_without_proxy:
            try:
                with without_proxy_env():
                    return func(**kwargs)
            except Exception as retry_exc:
                if is_proxy_error(exc):
                    raise retry_exc from exc
        raise


def call_akshare_unproxied(func: Callable[..., pd.DataFrame], **kwargs: Any) -> pd.DataFrame:
    with without_proxy_env():
        return func(**kwargs)


def fetch_stock_bars(
    ak: Any,
    *,
    code_or_instrument: str,
    start_date: str,
    end_date: str,
    adjust: str,
    timeout: float,
    retry_without_proxy: bool,
) -> tuple[pd.DataFrame, str, str, str]:
    code = strip_code(code_or_instrument)
    instrument = instrument_from_code(code)
    attempts = [
        (
            "stock_zh_a_hist",
            getattr(ak, "stock_zh_a_hist", None),
            {
                "symbol": code,
                "period": "daily",
                "start_date": ak_date(start_date),
                "end_date": ak_date(end_date),
                "adjust": adjust,
                "timeout": timeout,
            },
            "hands",
            "percent",
        ),
        (
            "stock_zh_a_daily",
            getattr(ak, "stock_zh_a_daily", None),
            {
                "symbol": akshare_symbol_with_market_prefix(code),
                "start_date": ak_date(start_date),
                "end_date": ak_date(end_date),
                "adjust": adjust,
            },
            "shares",
            "ratio",
        ),
        (
            "stock_zh_a_hist_tx",
            getattr(ak, "stock_zh_a_hist_tx", None),
            {
                "symbol": akshare_symbol_with_market_prefix(code),
                "start_date": ak_date(start_date),
                "end_date": ak_date(end_date),
                "adjust": adjust,
                "timeout": timeout,
            },
            "hands",
            "unknown",
        ),
    ]
    errors: list[str] = []
    for name, func, kwargs, volume_unit, turnover_unit in attempts:
        if func is None:
            errors.append(f"{name}: missing")
            continue
        try:
            df = call_akshare(func, retry_without_proxy=retry_without_proxy, **kwargs)
            if df.empty:
                raise ValueError("empty response")
            normalized = normalize_daily_bars(
                df,
                instrument=instrument,
                source_function=name,
                volume_unit=volume_unit,
                turnover_unit=turnover_unit,
            )
            return normalized, name, volume_unit, turnover_unit
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
    raise RuntimeError("; ".join(errors))


def audit_akshare_sources(
    ak: Any,
    *,
    requested_start: str,
    requested_end: str,
    sample_symbol: str = "600519",
    live: bool = True,
    retry_without_proxy: bool = True,
    timeout: float = 20.0,
) -> list[SourceAuditRow]:
    sample_start = "2024-05-06"
    sample_end = "2024-05-10"
    rows: list[SourceAuditRow] = []

    rows.append(
        _audit_daily_category(
            ak,
            category="historical_raw_daily_bars",
            sample_symbol=sample_symbol,
            sample_start=sample_start,
            sample_end=sample_end,
            adjust="",
            live=live,
            retry_without_proxy=retry_without_proxy,
            timeout=timeout,
        )
    )
    rows.append(
        _audit_daily_category(
            ak,
            category="historical_qfq_daily_bars",
            sample_symbol=sample_symbol,
            sample_start=sample_start,
            sample_end=sample_end,
            adjust="qfq",
            live=live,
            retry_without_proxy=retry_without_proxy,
            timeout=timeout,
        )
    )
    rows.append(
        _audit_share_category(
            ak,
            sample_symbol=sample_symbol,
            live=live,
            retry_without_proxy=retry_without_proxy,
        )
    )
    rows.append(_audit_instrument_metadata_category(ak, live=live, retry_without_proxy=retry_without_proxy))
    rows.append(_audit_listed_status_category(ak, live=live, retry_without_proxy=retry_without_proxy))
    rows.append(
        _audit_historical_st_category(
            ak,
            sample_symbol=sample_symbol,
            live=live,
            retry_without_proxy=retry_without_proxy,
        )
    )
    rows.append(
        _audit_suspension_category(
            ak,
            sample_date=sample_start,
            live=live,
            retry_without_proxy=retry_without_proxy,
        )
    )
    rows.append(
        _audit_trading_calendar_category(
            ak,
            requested_start=requested_start,
            requested_end=requested_end,
            live=live,
            retry_without_proxy=retry_without_proxy,
        )
    )
    return rows


def _not_evaluated(category: str, function_name: str, notes: str) -> SourceAuditRow:
    return SourceAuditRow(
        category=category,
        support_state="not_evaluated",
        function_name=function_name,
        fallback_state="live_audit_disabled",
        notes=notes,
    )


def _audit_daily_category(
    ak: Any,
    *,
    category: str,
    sample_symbol: str,
    sample_start: str,
    sample_end: str,
    adjust: str,
    live: bool,
    retry_without_proxy: bool,
    timeout: float,
) -> SourceAuditRow:
    if not live:
        return _not_evaluated(category, "stock_zh_a_hist", "Daily source was not sampled.")
    try:
        df, source_name, volume_unit, turnover_unit = fetch_stock_bars(
            ak,
            code_or_instrument=sample_symbol,
            start_date=sample_start,
            end_date=sample_end,
            adjust=adjust,
            timeout=timeout,
            retry_without_proxy=retry_without_proxy,
        )
        return SourceAuditRow(
            category=category,
            support_state="supported",
            function_name=source_name,
            source_columns=tuple(df.columns),
            units=f"volume={volume_unit};turnover={turnover_unit};money=CNY",
            source_date_field="date",
            historical=True,
            latest_only=False,
            fallback_state="primary_or_fallback_sampled",
            sample_rows=len(df),
            notes=f"Sampled {sample_start} through {sample_end}, adjust={adjust or 'raw'}.",
        )
    except Exception as exc:
        return SourceAuditRow(
            category=category,
            support_state="unsupported",
            function_name="stock_zh_a_hist|stock_zh_a_daily|stock_zh_a_hist_tx",
            historical=False,
            latest_only=False,
            fallback_state="all_daily_attempts_failed",
            notes=f"{type(exc).__name__}: {exc}",
        )


def _audit_share_category(
    ak: Any,
    *,
    sample_symbol: str,
    live: bool,
    retry_without_proxy: bool,
) -> SourceAuditRow:
    function_name = "stock_zh_a_gbjg_em"
    func = getattr(ak, function_name, None)
    if func is None:
        return SourceAuditRow(
            category="historical_total_market_cap_or_total_share_asof",
            support_state="unsupported",
            function_name=function_name,
            notes="AkShare function is missing.",
        )
    if not live:
        return _not_evaluated(
            "historical_total_market_cap_or_total_share_asof",
            function_name,
            "Share-structure source was not sampled.",
        )
    try:
        df = call_akshare(
            func,
            retry_without_proxy=retry_without_proxy,
            symbol=akshare_symbol_with_exchange_suffix(sample_symbol),
        )
        columns = tuple(map(str, df.columns))
        if {"变更日期", "总股本"}.issubset(df.columns):
            fallback_columns: tuple[str, ...] = ()
            fallback_rows = 0
            fallback_note = ""
            fallback_func = getattr(ak, "stock_share_change_cninfo", None)
            if fallback_func is not None:
                try:
                    fallback_df = call_akshare(
                        fallback_func,
                        retry_without_proxy=retry_without_proxy,
                        symbol=strip_code(sample_symbol),
                        start_date="19900101",
                        end_date="20260531",
                    )
                    fallback_columns = tuple(
                        f"stock_share_change_cninfo.{col}" for col in fallback_df.columns
                    )
                    fallback_rows = len(fallback_df)
                    fallback_note = (
                        " Fallback stock_share_change_cninfo sampled with "
                        "变动日期 and 总股本 in 10k-share units."
                    )
                except Exception as fallback_exc:
                    fallback_note = (
                        " Fallback stock_share_change_cninfo sample failed: "
                        f"{type(fallback_exc).__name__}: {fallback_exc}"
                    )
            return SourceAuditRow(
                category="historical_total_market_cap_or_total_share_asof",
                support_state="supported",
                function_name="stock_zh_a_gbjg_em|stock_share_change_cninfo",
                source_columns=columns + fallback_columns,
                units=(
                    "stock_zh_a_gbjg_em total_share_asof=shares; "
                    "stock_share_change_cninfo 总股本=10k shares; "
                    "market_cap=raw_close_CNY*total_share_asof"
                ),
                source_date_field="变更日期|变动日期",
                historical=True,
                latest_only=False,
                fallback_state="primary_gbjg_or_cninfo_share_change_fallback",
                sample_rows=len(df) + fallback_rows,
                notes="Historical share-change rows can be as-of expanded by trade date."
                + fallback_note,
            )
        return SourceAuditRow(
            category="historical_total_market_cap_or_total_share_asof",
            support_state="unsupported",
            function_name=function_name,
            source_columns=columns,
            sample_rows=len(df),
            notes="Required columns 变更日期 and 总股本 were not present.",
        )
    except Exception as exc:
        return SourceAuditRow(
            category="historical_total_market_cap_or_total_share_asof",
            support_state="unsupported",
            function_name=function_name,
            fallback_state="share_structure_sample_failed",
            notes=f"{type(exc).__name__}: {exc}",
        )


def _audit_instrument_metadata_category(
    ak: Any,
    *,
    live: bool,
    retry_without_proxy: bool,
) -> SourceAuditRow:
    functions = [
        "stock_info_sh_name_code",
        "stock_info_sz_name_code",
        "stock_info_sh_delist",
        "stock_info_sz_delist",
    ]
    if not live:
        return _not_evaluated(
            "instrument_metadata_board_classification",
            "|".join(functions),
            "Instrument metadata sources were not sampled.",
        )
    try:
        columns: list[str] = []
        rows = 0
        calls = [
            ("stock_info_sh_name_code", {"symbol": "主板A股"}),
            ("stock_info_sz_name_code", {"symbol": "A股列表"}),
            ("stock_info_sh_delist", {"symbol": "全部"}),
            ("stock_info_sz_delist", {"symbol": "终止上市公司"}),
        ]
        for name, kwargs in calls:
            func = getattr(ak, name, None)
            if func is None:
                raise AttributeError(name)
            df = call_akshare(func, retry_without_proxy=retry_without_proxy, **kwargs)
            rows += len(df)
            columns.extend(f"{name}.{col}" for col in df.columns)
        return SourceAuditRow(
            category="instrument_metadata_board_classification",
            support_state="supported",
            function_name="|".join(functions),
            source_columns=tuple(columns),
            units="code/name/listing_date/delist_date where available",
            source_date_field="上市日期|暂停上市日期|终止上市日期",
            historical=True,
            latest_only=False,
            fallback_state="current_lists_plus_delist_lists",
            sample_rows=rows,
            notes="Board classification is code-prefix based after excluding non-target prefixes.",
        )
    except Exception as exc:
        return SourceAuditRow(
            category="instrument_metadata_board_classification",
            support_state="unsupported",
            function_name="|".join(functions),
            notes=f"{type(exc).__name__}: {exc}",
        )


def _audit_listed_status_category(
    ak: Any,
    *,
    live: bool,
    retry_without_proxy: bool,
) -> SourceAuditRow:
    if not live:
        return _not_evaluated(
            "historical_listed_delisted_status",
            "stock_info_sh_name_code|stock_info_sz_name_code|stock_info_sh_delist|stock_info_sz_delist",
            "Listing and delisting sources were not sampled.",
        )
    metadata = _audit_instrument_metadata_category(
        ak, live=live, retry_without_proxy=retry_without_proxy
    )
    return SourceAuditRow(
        category="historical_listed_delisted_status",
        support_state=metadata.support_state,
        function_name=metadata.function_name,
        source_columns=metadata.source_columns,
        units=metadata.units,
        source_date_field=metadata.source_date_field,
        historical=metadata.historical,
        latest_only=metadata.latest_only,
        fallback_state=metadata.fallback_state,
        sample_rows=metadata.sample_rows,
        notes="Listing status can be constructed from listing/delist dates when metadata audit passes.",
    )


def _audit_historical_st_category(
    ak: Any,
    *,
    sample_symbol: str,
    live: bool,
    retry_without_proxy: bool,
) -> SourceAuditRow:
    del retry_without_proxy
    functions = "stock_info_sz_change_name|stock_info_change_name|stock_zh_a_st_em"
    sh_st_probe_symbols = ("600003", "600608", "600193", "600145")
    if not live:
        return _not_evaluated(
            "historical_st_status", functions, "Historical ST sources were not sampled."
        )
    try:
        sz_func = getattr(ak, "stock_info_sz_change_name", None)
        sh_func = getattr(ak, "stock_info_change_name", None)
        current_st_func = getattr(ak, "stock_zh_a_st_em", None)
        if sz_func is None or sh_func is None:
            raise AttributeError("stock_info_sz_change_name or stock_info_change_name")
        sz_df = call_akshare_unproxied(
            sz_func,
            symbol="简称变更",
        )
        try:
            sh_df = call_akshare_unproxied(
                sh_func,
                symbol=strip_code(sample_symbol),
            )
            sh_sample_note = ""
        except Exception as exc:
            if "No tables found" not in str(exc):
                raise
            sh_df = pd.DataFrame(
                columns=["name", "source_note"],
                data=[
                    {
                        "name": "",
                        "source_note": "akshare_no_tables_found_interpreted_as_no_recorded_sh_name_change",
                    }
                ],
            )
            sh_sample_note = (
                f" Shanghai sample {strip_code(sample_symbol)} returned no name-history table; "
                "interpreted as no recorded Shanghai name-change rows for that symbol."
            )
        sh_st_probe_symbol = ""
        sh_st_probe_df = pd.DataFrame()
        probe_notes: list[str] = []
        for probe_symbol in sh_st_probe_symbols:
            try:
                probe_df = call_akshare_unproxied(sh_func, symbol=probe_symbol)
                if has_any_st_name_marker(probe_df):
                    sh_st_probe_symbol = probe_symbol
                    sh_st_probe_df = probe_df
                    break
                probe_notes.append(f"{probe_symbol}: no ST marker")
            except Exception as probe_exc:
                probe_notes.append(
                    f"{probe_symbol}: {type(probe_exc).__name__}: {probe_exc}"
                )
        current_columns: tuple[str, ...] = ()
        current_rows: int | None = None
        current_note = ""
        if current_st_func is not None:
            try:
                current_df = call_akshare_unproxied(
                    current_st_func,
                )
                current_columns = tuple(f"stock_zh_a_st_em.{col}" for col in current_df.columns)
                current_rows = len(current_df)
            except Exception as exc:
                current_note = f" Current ST list sample failed: {type(exc).__name__}: {exc}"
        columns = tuple(f"stock_info_sz_change_name.{col}" for col in sz_df.columns)
        columns += tuple(f"stock_info_change_name.{col}" for col in sh_df.columns)
        columns += tuple(f"stock_info_change_name_st_probe.{col}" for col in sh_st_probe_df.columns)
        columns += current_columns
        sz_required = {"变更日期", "证券代码", "变更前简称", "变更后简称"}
        sz_st_rows = count_dated_st_name_change_rows(sz_df) if sz_required.issubset(sz_df.columns) else 0
        sh_has_name_history = "name" in sh_df.columns
        sh_st_probe_has_marker = has_any_st_name_marker(sh_st_probe_df)
        if sz_required.issubset(sz_df.columns) and sh_has_name_history:
            return SourceAuditRow(
                category="historical_st_status",
                support_state="supported",
                function_name=functions,
                source_columns=columns,
                units=(
                    "SZ dated ST name changes; SH lifetime exclusion when any "
                    "stock_info_change_name row contains ST"
                ),
                source_date_field="SZ: 变更日期; SH: no date, whole-asset exclusion",
                historical=True,
                latest_only=False,
                fallback_state="supported_with_sh_lifetime_st_exclusion",
                sample_rows=len(sz_df) + len(sh_df) + len(sh_st_probe_df) + (current_rows or 0),
                notes=(
                    "Unproxied historical ST probe found "
                    f"{sz_st_rows} dated Shenzhen ST-name-change rows, but "
                    "Shanghai stock_info_change_name returns names without dates. "
                    "Policy: remove every Shanghai asset from the whole universe "
                    "when any returned name contains an ST marker; when AkShare "
                    "returns no Shanghai name-history table for a symbol, treat it "
                    "as no recorded Shanghai name-change rows for that symbol. "
                )
                + (
                    f"Probe {sh_st_probe_symbol} confirmed a Shanghai ST marker."
                    if sh_st_probe_has_marker
                    else "Shanghai ST marker probe did not confirm a marker in this run."
                )
                + sh_sample_note
                + (" Probe attempts: " + "; ".join(probe_notes) if probe_notes else "")
                + current_note,
            )
        if sz_required.issubset(sz_df.columns) and "变更日期" not in sh_df.columns:
            return SourceAuditRow(
                category="historical_st_status",
                support_state="unsupported",
                function_name=functions,
                source_columns=columns,
                units="SZ name changes are dated; SH name-change sample has no dates",
                source_date_field="变更日期 only for stock_info_sz_change_name",
                historical=False,
                latest_only=True,
                fallback_state="sh_lifetime_st_exclusion_probe_failed",
                sample_rows=len(sz_df) + len(sh_df) + len(sh_st_probe_df) + (current_rows or 0),
                notes=(
                    "Shenzhen dated ST history was available, but the Shanghai "
                    "whole-asset exclusion probe did not confirm an ST marker."
                )
                + current_note,
            )
        return SourceAuditRow(
            category="historical_st_status",
            support_state="unsupported",
            function_name=functions,
            source_columns=columns,
            historical=False,
            latest_only=True,
            fallback_state="historical_st_dates_not_resolved",
            sample_rows=len(sz_df) + len(sh_df) + (current_rows or 0),
            notes="No complete dated ST source was resolved.",
        )
    except Exception as exc:
        return SourceAuditRow(
            category="historical_st_status",
            support_state="unsupported",
            function_name=functions,
            fallback_state="st_source_sample_failed",
            notes=f"{type(exc).__name__}: {exc}",
        )


def _audit_suspension_category(
    ak: Any,
    *,
    sample_date: str,
    live: bool,
    retry_without_proxy: bool,
) -> SourceAuditRow:
    function_name = "stock_tfp_em"
    func = getattr(ak, function_name, None)
    if func is None:
        return SourceAuditRow(
            category="suspension_or_tradability_status",
            support_state="unsupported",
            function_name=function_name,
            notes="AkShare function is missing.",
        )
    if not live:
        return _not_evaluated(
            "suspension_or_tradability_status",
            function_name,
            "Suspension source was not sampled.",
        )
    try:
        df = call_akshare(
            func,
            retry_without_proxy=retry_without_proxy,
            date=ak_date(sample_date),
        )
        columns = tuple(map(str, df.columns))
        historical = suspension_sample_matches_requested_date(df, sample_date)
        return SourceAuditRow(
            category="suspension_or_tradability_status",
            support_state="supported" if historical else "unsupported",
            function_name=function_name,
            source_columns=columns,
            units="suspension rows keyed by requested trade date" if historical else "latest/current rows",
            source_date_field="停牌时间|停牌截止时间",
            historical=historical,
            latest_only=not historical,
            fallback_state="sample_date_respected" if historical else "date_parameter_not_respected_or_unverifiable",
            sample_rows=len(df),
            notes=(
                f"Sample for {sample_date} matched requested date."
                if historical
                else f"Sample for {sample_date} did not provide auditable same-date suspension status."
            ),
        )
    except Exception as exc:
        return SourceAuditRow(
            category="suspension_or_tradability_status",
            support_state="unsupported",
            function_name=function_name,
            fallback_state="suspension_source_sample_failed",
            notes=f"{type(exc).__name__}: {exc}",
        )


def suspension_sample_matches_requested_date(df: pd.DataFrame, requested_date: str) -> bool:
    if df.empty:
        return False
    if "停牌时间" not in df.columns:
        return False
    requested = parse_date(requested_date)
    start = pd.to_datetime(df["停牌时间"], errors="coerce")
    end = pd.to_datetime(df.get("停牌截止时间", df["停牌时间"]), errors="coerce")
    if start.notna().sum() == 0:
        return False
    covers_requested = ((start <= requested) & ((end.isna()) | (end >= requested))).any()
    exact_requested = (start.dt.normalize() == requested).any()
    return bool(covers_requested or exact_requested)


def has_st_name_marker(value: Any) -> bool:
    text = str(value).upper()
    text = text.replace("＊", "*").replace("Ｓ", "S").replace("Ｔ", "T")
    return "ST" in text


def has_any_st_name_marker(df: pd.DataFrame, columns: Iterable[str] | None = None) -> bool:
    if df.empty:
        return False
    marker_columns = list(columns or [column for column in ["name", "名称", "证券简称", "变更前简称", "变更后简称"] if column in df.columns])
    if not marker_columns:
        return False
    marker = pd.Series(False, index=df.index)
    for column in marker_columns:
        marker = marker | df[column].map(has_st_name_marker)
    return bool(marker.any())


def count_dated_st_name_change_rows(df: pd.DataFrame) -> int:
    marker_columns = [column for column in ["证券简称", "变更前简称", "变更后简称"] if column in df.columns]
    if "变更日期" not in df.columns or not marker_columns:
        return 0
    dated = pd.to_datetime(df["变更日期"], errors="coerce").notna()
    marker = pd.Series(False, index=df.index)
    for column in marker_columns:
        marker = marker | df[column].map(has_st_name_marker)
    return int((dated & marker).sum())


def _audit_trading_calendar_category(
    ak: Any,
    *,
    requested_start: str,
    requested_end: str,
    live: bool,
    retry_without_proxy: bool,
) -> SourceAuditRow:
    function_name = "tool_trade_date_hist_sina"
    func = getattr(ak, function_name, None)
    if func is None:
        return SourceAuditRow(
            category="trading_calendar",
            support_state="unsupported",
            function_name=function_name,
            notes="AkShare function is missing.",
        )
    if not live:
        return _not_evaluated(
            "trading_calendar", function_name, "Trading calendar was not sampled."
        )
    try:
        df = call_akshare(func, retry_without_proxy=retry_without_proxy)
        columns = tuple(map(str, df.columns))
        if "trade_date" not in df.columns:
            raise ValueError("trade_date column missing")
        resolved = resolve_trade_calendar(df["trade_date"], requested_start, requested_end)
        return SourceAuditRow(
            category="trading_calendar",
            support_state="supported",
            function_name=function_name,
            source_columns=columns,
            units="A-share trading session date",
            source_date_field="trade_date",
            historical=True,
            latest_only=False,
            fallback_state="calendar_covers_requested_range",
            sample_rows=len(df),
            notes=f"Resolved {len(resolved)} sessions from {resolved[0]} to {resolved[-1]}.",
        )
    except Exception as exc:
        return SourceAuditRow(
            category="trading_calendar",
            support_state="unsupported",
            function_name=function_name,
            fallback_state="calendar_sample_failed",
            notes=f"{type(exc).__name__}: {exc}",
        )


def blocking_audit_issues(rows: Iterable[SourceAuditRow], *, require_evaluated: bool) -> list[SourceAuditRow]:
    blocking_states = {"unsupported", "partial"}
    if require_evaluated:
        blocking_states.add("not_evaluated")
    return [row for row in rows if row.support_state in blocking_states]


def audit_rows_to_frame(rows: Iterable[SourceAuditRow]) -> pd.DataFrame:
    return pd.DataFrame([row.as_dict() for row in rows])


def write_audit_report(rows: Iterable[SourceAuditRow], path: Path, *, require_evaluated: bool) -> None:
    rows = list(rows)
    blocking = blocking_audit_issues(rows, require_evaluated=require_evaluated)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AkShare API Audit",
        "",
        f"Blocking issues: {len(blocking)}",
        "",
        "| category | support_state | function_name | historical | latest_only | fallback_state | notes |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _md(row.category),
                    _md(row.support_state),
                    _md(row.function_name),
                    str(row.historical),
                    str(row.latest_only),
                    _md(row.fallback_state),
                    _md(row.notes),
                ]
            )
            + " |"
        )
    if blocking:
        lines.extend(["", "## Blocking Categories", ""])
        for row in blocking:
            lines.append(f"- `{row.category}`: {row.notes}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def write_qlib_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, columns=QLIB_COLUMNS, float_format="%.10g")
