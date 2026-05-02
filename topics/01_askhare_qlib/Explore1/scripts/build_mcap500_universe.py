#!/usr/bin/env python
from __future__ import annotations

import argparse
import math
import sys
import time
from datetime import timedelta

import pandas as pd
import requests

from explore1_utils import instrument_from_code, qlib_symbol, relpath, topic_path, write_qlib_instruments


MAINBOARD_SH_PREFIXES = ("600", "601", "603", "605")
MAINBOARD_SZ_PREFIXES = ("000", "001", "002", "003")
EXCLUDED_PREFIXES = ("200", "300", "301", "688", "689", "4", "8", "900")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Explore1 static mainboard market-cap universe.")
    parser.add_argument("--base-date", default="2025-12-31")
    parser.add_argument("--start-date", default="2017-01-01", help="Start date for generated Qlib instruments.")
    parser.add_argument("--end-date", default="2026-04-30", help="End date for generated Qlib instruments.")
    parser.add_argument("--threshold", type=float, default=50_000_000_000.0)
    parser.add_argument("--price-lookback-days", type=int, default=10)
    parser.add_argument("--output", default="Explore1/data/universe/mcap500_mainboard_20251231.csv")
    parser.add_argument("--instrument-output", default="Explore1/data/universe/qlib_mcap500_mainboard_20251231.txt")
    parser.add_argument("--audit-output", default="Explore1/outputs/reports/mcap500_universe_audit.csv")
    parser.add_argument("--candidates-output", default="Explore1/outputs/reports/mcap500_universe_candidates.csv")
    parser.add_argument("--symbols", nargs="*", help="Optional stock codes or Qlib instruments to process.")
    parser.add_argument("--limit", type=int, help="Process only the first N filtered candidates.")
    parser.add_argument("--sleep", type=float, default=0.1)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--spot-retries", type=int, default=3)
    parser.add_argument("--spot-retry-sleep", type=float, default=3.0)
    parser.add_argument("--fail-fast", action="store_true")
    return parser.parse_args()


def clean_code(value: object) -> str:
    digits = "".join(ch for ch in str(value).upper() if ch.isdigit())
    if not digits:
        raise ValueError(f"invalid stock code {value!r}")
    return digits.zfill(6)


def exchange_from_code(code: str) -> str:
    return "SH" if code.startswith("6") else "SZ"


def sina_symbol(code: str) -> str:
    return f"sh{code}" if code.startswith("6") else f"sz{code}"


def is_mainboard(code: str) -> bool:
    return code.startswith(MAINBOARD_SH_PREFIXES) or code.startswith(MAINBOARD_SZ_PREFIXES)


def excluded_by_prefix(code: str) -> bool:
    return code.startswith(EXCLUDED_PREFIXES)


def excluded_by_name(name: object) -> bool:
    text = str(name).upper().strip()
    return "ST" in text or "退" in text


def normalize_spot(df: pd.DataFrame) -> pd.DataFrame:
    required = {"代码", "名称"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"stock_zh_a_spot_em missing columns: {sorted(missing)}")
    out = df.copy()
    out["code"] = out["代码"].map(clean_code)
    out["name"] = out["名称"].astype(str)
    out["exchange"] = out["code"].map(exchange_from_code)
    out["instrument"] = out.apply(lambda row: instrument_from_code(row["code"], row["exchange"]), axis=1)
    return out.drop_duplicates("instrument").reset_index(drop=True)


def fetch_spot_direct_page(timeout: float, page: int, page_size: int = 100) -> tuple[list[dict[str, object]], int]:
    url = "https://82.push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": str(page),
        "pz": str(page_size),
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f12",
        "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
        "fields": "f12,f14",
    }
    response = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    data = response.json().get("data") or {}
    rows = data.get("diff") or []
    total = int(data.get("total") or len(rows))
    if not rows:
        raise RuntimeError(f"direct Eastmoney spot request returned no rows for page {page}")
    return rows, total


def fetch_spot_direct(timeout: float, retries: int, retry_sleep: float) -> pd.DataFrame:
    page_size = 100
    all_rows: list[dict[str, object]] = []
    first_rows, total = fetch_spot_direct_page(timeout, 1, page_size)
    all_rows.extend(first_rows)
    page_count = max(1, math.ceil(total / page_size))
    for page in range(2, page_count + 1):
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                rows, _ = fetch_spot_direct_page(timeout, page, page_size)
                all_rows.extend(rows)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(retry_sleep)
        if last_error is not None:
            raise last_error
    return pd.DataFrame(all_rows).rename(columns={"f12": "代码", "f14": "名称"})


def fetch_spot_table(ak, timeout: float, retries: int, retry_sleep: float) -> pd.DataFrame:
    errors: list[str] = []
    for attempt in range(1, retries + 1):
        try:
            return fetch_spot_direct(timeout, retries, retry_sleep)
        except Exception as exc:
            errors.append(f"direct attempt {attempt}: {exc}")
            if attempt < retries:
                time.sleep(retry_sleep)
    try:
        return ak.stock_zh_a_spot()
    except Exception as exc:
        errors.append(f"akshare sina fallback: {exc}")
    try:
        return ak.stock_zh_a_spot_em()
    except Exception as exc:
        errors.append(f"akshare eastmoney fallback: {exc}")
    raise RuntimeError("; ".join(errors))


def select_candidates(spot: pd.DataFrame, symbols: list[str] | None, limit: int | None) -> pd.DataFrame:
    rows = spot.copy()
    rows["candidate_reason"] = ""
    mask = rows["code"].map(is_mainboard)
    rows.loc[~mask, "candidate_reason"] = "excluded_prefix_or_non_mainboard"
    mask &= ~rows["code"].map(excluded_by_prefix)
    rows.loc[rows["code"].map(excluded_by_prefix), "candidate_reason"] = "excluded_prefix"
    mask &= ~rows["name"].map(excluded_by_name)
    rows.loc[rows["name"].map(excluded_by_name), "candidate_reason"] = "excluded_name"
    rows = rows[mask].copy()

    if symbols:
        wanted = {instrument_from_code(clean_code(symbol)) for symbol in symbols}
        rows = rows[rows["instrument"].isin(wanted)].copy()
        missing = sorted(wanted.difference(set(rows["instrument"])))
        if missing:
            raise ValueError(f"Symbols not found after mainboard/ST filters: {missing}")
    if limit is not None:
        rows = rows.head(limit).copy()
    return rows.reset_index(drop=True)


def _pick_base_close(df: pd.DataFrame, base_date: pd.Timestamp) -> tuple[pd.Timestamp, float]:
    if df.empty:
        raise RuntimeError("empty price table")
    date_col = "日期" if "日期" in df.columns else "date"
    close_col = "收盘" if "收盘" in df.columns else "close"
    if date_col not in df.columns or close_col not in df.columns:
        raise RuntimeError(f"missing {date_col!r} or {close_col!r}")
    prices = df[[date_col, close_col]].copy()
    prices[date_col] = pd.to_datetime(prices[date_col], errors="coerce")
    prices[close_col] = pd.to_numeric(prices[close_col], errors="coerce")
    prices = prices.dropna().sort_values(date_col)
    prices = prices[prices[date_col] <= base_date]
    if prices.empty:
        raise RuntimeError("no usable close on or before base date")
    last = prices.iloc[-1]
    return pd.Timestamp(last[date_col]), float(last[close_col])


def fetch_base_close(ak, code: str, base_date: pd.Timestamp, lookback_days: int, timeout: float) -> tuple[pd.Timestamp, float]:
    start_date = (base_date - timedelta(days=lookback_days)).strftime("%Y%m%d")
    end_date = base_date.strftime("%Y%m%d")
    errors: list[str] = []
    try:
        df = ak.stock_zh_a_daily(
            symbol=sina_symbol(code),
            start_date=start_date,
            end_date=end_date,
            adjust="",
        )
        return _pick_base_close(df, base_date)
    except Exception as exc:
        errors.append(f"stock_zh_a_daily: {exc}")

    try:
        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="",
            timeout=timeout,
        )
        return _pick_base_close(df, base_date)
    except Exception as exc:
        errors.append(f"stock_zh_a_hist: {exc}")

    raise RuntimeError("; ".join(errors))


def _pick_total_shares(df: pd.DataFrame, date_column: str, shares_column: str, base_date: pd.Timestamp) -> tuple[pd.Timestamp, float]:
    if df.empty:
        raise RuntimeError("empty shares table")
    if date_column not in df.columns or shares_column not in df.columns:
        raise RuntimeError(f"missing {date_column!r} or {shares_column!r}")
    shares = df[[date_column, shares_column]].copy()
    shares[date_column] = pd.to_datetime(shares[date_column], errors="coerce")
    shares[shares_column] = pd.to_numeric(shares[shares_column], errors="coerce")
    shares = shares.dropna().sort_values(date_column)
    shares = shares[(shares[date_column] <= base_date) & (shares[shares_column] > 0)]
    if shares.empty:
        raise RuntimeError("no effective shares on or before base date")
    last = shares.iloc[-1]
    return pd.Timestamp(last[date_column]), float(last[shares_column])


def fetch_total_shares(ak, code: str, exchange: str, base_date: pd.Timestamp) -> tuple[pd.Timestamp, float, str]:
    errors: list[str] = []
    try:
        df = ak.stock_zh_a_gbjg_em(symbol=qlib_symbol(code, exchange))
        date_value, total_shares = _pick_total_shares(df, "变更日期", "总股本", base_date)
        return date_value, total_shares, "stock_zh_a_gbjg_em"
    except Exception as exc:
        errors.append(f"stock_zh_a_gbjg_em: {exc}")

    try:
        df = ak.stock_share_change_cninfo(
            symbol=code,
            start_date="19900101",
            end_date=base_date.strftime("%Y%m%d"),
        )
        date_value, total_shares = _pick_total_shares(df, "变动日期", "总股本", base_date)
        return date_value, total_shares, "stock_share_change_cninfo"
    except Exception as exc:
        errors.append(f"stock_share_change_cninfo: {exc}")

    raise RuntimeError("; ".join(errors))


def validate_universe(universe: pd.DataFrame, threshold: float) -> None:
    if universe.empty:
        raise RuntimeError("universe is empty")
    invalid_codes = universe[~universe["code"].map(is_mainboard) | universe["code"].map(excluded_by_prefix)]
    if not invalid_codes.empty:
        raise RuntimeError(f"non-mainboard or excluded codes survived: {invalid_codes['instrument'].tolist()[:10]}")
    invalid_names = universe[universe["name"].map(excluded_by_name)]
    if not invalid_names.empty:
        raise RuntimeError(f"ST/delisting names survived: {invalid_names['instrument'].tolist()[:10]}")
    below = universe[pd.to_numeric(universe["market_cap"], errors="coerce") < threshold]
    if not below.empty:
        raise RuntimeError(f"market cap below threshold survived: {below['instrument'].tolist()[:10]}")


def main() -> int:
    args = parse_args()
    import akshare as ak

    base_date = pd.Timestamp(args.base_date)
    spot = normalize_spot(fetch_spot_table(ak, args.timeout, args.spot_retries, args.spot_retry_sleep))
    spot_path = topic_path(args.candidates_output)
    spot_path.parent.mkdir(parents=True, exist_ok=True)

    candidates = select_candidates(spot, args.symbols, args.limit)
    candidates.to_csv(spot_path, index=False)
    print(f"wrote {relpath(spot_path)} rows={len(candidates)}")

    audit_rows: list[dict[str, object]] = []
    for idx, row in enumerate(candidates.itertuples(index=False), start=1):
        item = {
            "code": row.code,
            "name": row.name,
            "instrument": row.instrument,
            "exchange": row.exchange,
            "base_date": args.base_date,
        }
        try:
            price_date, close = fetch_base_close(ak, row.code, base_date, args.price_lookback_days, args.timeout)
            shares_date, total_shares, shares_source = fetch_total_shares(ak, row.code, row.exchange, base_date)
            market_cap = close * total_shares
            item.update(
                price_date=price_date.date().isoformat(),
                close=close,
                shares_date=shares_date.date().isoformat(),
                total_shares=total_shares,
                shares_source=shares_source,
                market_cap=market_cap,
                included=market_cap >= args.threshold,
                reason="" if market_cap >= args.threshold else "below_threshold",
            )
        except Exception as exc:
            item.update(included=False, reason=str(exc))
            print(f"ERROR {row.instrument}: {exc}", file=sys.stderr)
            if args.fail_fast:
                audit_rows.append(item)
                break
        audit_rows.append(item)
        if args.sleep and idx < len(candidates):
            time.sleep(args.sleep)

    audit = pd.DataFrame(audit_rows)
    audit_path = topic_path(args.audit_output)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(audit_path, index=False)
    print(f"wrote {relpath(audit_path)} rows={len(audit)}")

    included = audit[audit["included"] == True].copy()  # noqa: E712
    output_columns = [
        "code",
        "name",
        "instrument",
        "exchange",
        "base_date",
        "price_date",
        "close",
        "shares_date",
        "total_shares",
        "shares_source",
        "market_cap",
    ]
    universe = included[output_columns].sort_values("market_cap", ascending=False).reset_index(drop=True)
    validate_universe(universe, args.threshold)

    output_path = topic_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    universe.to_csv(output_path, index=False)
    write_qlib_instruments(universe, args.instrument_output, args.start_date, args.end_date)
    print(f"wrote {relpath(output_path)} rows={len(universe)}")
    print(f"wrote {relpath(topic_path(args.instrument_output))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
