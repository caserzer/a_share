from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

import pandas as pd


TOPIC_DIR = Path(os.environ.get("TOPIC_DIR", Path(__file__).resolve().parents[1])).resolve()
UNIVERSE_CSV = TOPIC_DIR / "data" / "universe" / "selected_stock_pool.csv"


@dataclass(frozen=True)
class Instrument:
    code: str
    name: str
    instrument: str
    exchange: str


def topic_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return TOPIC_DIR / path


def parse_date(value: str) -> date:
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Invalid date {value!r}; expected YYYY-MM-DD or YYYYMMDD")


def ak_date(value: str | date) -> str:
    parsed = value if isinstance(value, date) else parse_date(value)
    return parsed.strftime("%Y%m%d")


def qlib_date(value: str | date) -> str:
    parsed = value if isinstance(value, date) else parse_date(value)
    return parsed.isoformat()


def exchange_from_code(code: str) -> str:
    digits = strip_market_prefix(code)
    if digits.startswith(("4", "8")):
        return "BJ"
    if digits.startswith(("0", "2", "3")):
        return "SZ"
    if digits.startswith(("5", "6", "9")):
        return "SH"
    raise ValueError(f"Cannot infer exchange for code {code!r}")


def strip_market_prefix(code_or_instrument: str) -> str:
    text = str(code_or_instrument).strip().upper()
    if text.startswith(("SH", "SZ", "BJ")):
        text = text[2:]
    if "." in text:
        first, second = text.split(".", 1)
        text = second if first in {"SH", "SZ", "BJ"} else first
    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        raise ValueError(f"No numeric code found in {code_or_instrument!r}")
    return digits.zfill(6)


def instrument_from_code(code: str, exchange: str | None = None) -> str:
    digits = strip_market_prefix(code)
    market = exchange or exchange_from_code(digits)
    return f"{market.upper()}{digits}"


def akshare_index_symbol(instrument: str) -> str:
    market = instrument[:2].lower()
    code = instrument[2:]
    return f"{market}{code}"


def load_universe(path: str | Path = UNIVERSE_CSV) -> pd.DataFrame:
    universe_path = topic_path(path)
    df = pd.read_csv(universe_path, dtype={"code": "string", "instrument": "string", "exchange": "string"})
    required = {"code", "name", "instrument", "exchange"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"{universe_path} missing columns: {sorted(missing)}")
    df["code"] = df["code"].map(strip_market_prefix)
    df["exchange"] = df["exchange"].str.upper()
    df["instrument"] = df.apply(
        lambda row: instrument_from_code(row["code"], row["exchange"]),
        axis=1,
    )
    return df.drop_duplicates("instrument").reset_index(drop=True)


def filter_universe(df: pd.DataFrame, symbols: Iterable[str] | None, limit: int | None = None) -> pd.DataFrame:
    selected = df
    if symbols:
        wanted = {instrument_from_code(symbol) for symbol in symbols}
        selected = selected[selected["instrument"].isin(wanted)]
        missing = sorted(wanted.difference(set(selected["instrument"])))
        if missing:
            raise ValueError(f"Symbols not found in universe: {missing}")
    if limit is not None:
        selected = selected.head(limit)
    return selected.reset_index(drop=True)


def write_qlib_instrument_file(df: pd.DataFrame, path: str | Path, start_date: str, end_date: str) -> None:
    output_path = topic_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    start = qlib_date(start_date)
    end = qlib_date(end_date)
    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        for instrument in df["instrument"]:
            file.write(f"{instrument}\t{start}\t{end}\n")

