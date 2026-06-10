from __future__ import annotations

import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

MAIN_BOARD_PREFIXES = ("000", "001", "002", "003", "600", "601", "603", "605")
CHINEXT_PREFIXES = ("300", "301")
EXCLUDED_PREFIXES = ("688", "689")
ALLOWED_BUCKETS = ("main_board", "chinext")

MEMBERSHIP_COLUMNS = [
    "membership_date",
    "available_time",
    "membership_available_time",
    "usable_trade_date",
    "instrument",
    "ts_code",
    "board_bucket",
    "is_listed",
    "is_st",
    "is_suspended",
    "raw_unadjusted_close",
    "total_share_asof",
    "total_market_cap_cny",
    "market_cap_source",
    "price_source",
    "share_source",
    "status_source",
    "source_trade_date",
    "source_asof_date",
    "candidate_universe_source",
    "membership_rule_version",
    "board_rank_by_market_cap",
    "board_quota",
    "quota_fill_rate",
    "quota_shortfall_count",
    "quota_shortfall_reason",
    "rank_cutoff_market_cap_cny",
    "rank_rule_version",
    "minimum_history_sessions",
    "history_observed_sessions_before_usable_date",
    "history_ready_240d_flag",
    "history_ready_missing_reason",
]

EXECUTABLE_COLUMNS = [
    "usable_trade_date",
    "instrument",
    "source_membership_date",
    "membership_date",
    "membership_available_time",
    "available_time",
    "ts_code",
    "board_bucket",
    "is_listed",
    "is_st",
    "is_suspended",
    "raw_unadjusted_close",
    "total_share_asof",
    "total_market_cap_cny",
    "market_cap_source",
    "price_source",
    "share_source",
    "status_source",
    "source_trade_date",
    "source_asof_date",
    "candidate_universe_source",
    "membership_rule_version",
    "board_rank_by_market_cap",
    "board_quota",
    "quota_fill_rate",
    "quota_shortfall_count",
    "quota_shortfall_reason",
    "rank_cutoff_market_cap_cny",
    "rank_rule_version",
    "minimum_history_sessions",
    "history_observed_sessions_before_usable_date",
    "history_ready_240d_flag",
    "history_ready_missing_reason",
]


class TopNUniverseBlocked(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class BuildInputs:
    candidate: pd.DataFrame
    source_audit: pd.DataFrame
    active_listing_counts: pd.DataFrame
    calendar: list[str]
    next_trade_date: dict[str, str | None]
    source_gap_count: int
    active_source_gap_count: int


@dataclass(frozen=True)
class TopNResult:
    membership: pd.DataFrame
    executable: pd.DataFrame
    intervals: pd.DataFrame
    daily_counts: pd.DataFrame
    board_counts: pd.DataFrame
    yearly_summary: pd.DataFrame
    quota_fill_audit: pd.DataFrame
    rank_cutoff_audit: pd.DataFrame
    status_exclusion_audit: pd.DataFrame
    history_coverage_audit: pd.DataFrame
    fixed_cap_overlap_audit: pd.DataFrame
    topn_only_vs_fixed_cap_only_audit: pd.DataFrame
    gate_summary: dict[str, Any]


def numeric_series(values: pd.Series) -> pd.Series:
    text = values.astype("string").str.replace(",", "", regex=False)
    text = text.str.replace("%", "", regex=False).str.strip()
    return pd.to_numeric(text, errors="coerce")


def parse_date(value: str | pd.Timestamp) -> pd.Timestamp:
    if isinstance(value, pd.Timestamp):
        return value.normalize()
    return pd.to_datetime(str(value), errors="raise").normalize()


def strip_code(value: Any) -> str:
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


def exchange_from_code(code_or_instrument: Any) -> str:
    code = strip_code(code_or_instrument)
    if code.startswith(("0", "2", "3")):
        return "SZ"
    if code.startswith(("5", "6", "9")):
        return "SH"
    if code.startswith(("4", "8")):
        return "BJ"
    raise ValueError(f"Cannot infer exchange from {code_or_instrument!r}")


def instrument_from_code(code_or_instrument: Any) -> str:
    code = strip_code(code_or_instrument)
    return f"{exchange_from_code(code)}{code}"


def board_bucket(code_or_instrument: Any) -> str | None:
    code = strip_code(code_or_instrument)
    if code.startswith(EXCLUDED_PREFIXES):
        return None
    if code.startswith(MAIN_BOARD_PREFIXES):
        return "main_board"
    if code.startswith(CHINEXT_PREFIXES):
        return "chinext"
    return None


def has_st_name_marker(value: Any) -> bool:
    text = str(value).upper()
    text = text.replace("＊", "*").replace("Ｓ", "S").replace("Ｔ", "T")
    return "ST" in text


def has_any_st_name_marker(
    df: pd.DataFrame, columns: Iterable[str] | None = None
) -> bool:
    if df.empty:
        return False
    marker_columns = list(
        columns
        or [
            column
            for column in ["name", "名称", "证券简称", "变更前简称", "变更后简称"]
            if column in df.columns
        ]
    )
    if not marker_columns:
        return False
    marker = pd.Series(False, index=df.index)
    for column in marker_columns:
        marker = marker | df[column].map(has_st_name_marker)
    return bool(marker.any())


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision(cwd: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def require_columns(df: pd.DataFrame, required: Iterable[str], frame_name: str) -> None:
    missing = set(required).difference(df.columns)
    if missing:
        raise TopNUniverseBlocked(
            "topn_universe_source_blocked",
            f"{frame_name} missing required columns: {sorted(missing)}",
        )


def bool_series(values: pd.Series) -> pd.Series:
    if values.dtype == bool:
        return values.fillna(False)
    return values.astype("string").str.lower().isin({"true", "1", "yes", "y"})


def load_trade_calendar(
    calendar_path: Path, requested_start: str, requested_end: str
) -> list[str]:
    if not calendar_path.is_file():
        raise TopNUniverseBlocked(
            "topn_universe_pit_clock_blocked",
            f"trading calendar is missing: {calendar_path}",
        )
    calendar = pd.read_csv(calendar_path, dtype="string")
    column = "trade_date" if "trade_date" in calendar.columns else "date"
    require_columns(calendar, [column], "trading_calendar")
    start = parse_date(requested_start)
    end = parse_date(requested_end)
    dates = pd.to_datetime(calendar[column], errors="coerce").dropna().dt.normalize()
    resolved = sorted(value.strftime("%Y-%m-%d") for value in dates if start <= value <= end)
    if not resolved:
        raise TopNUniverseBlocked(
            "topn_universe_pit_clock_blocked",
            "trading calendar has no sessions in requested range",
        )
    return resolved


def next_trade_date_map(calendar: Iterable[str]) -> dict[str, str | None]:
    sessions = list(calendar)
    return {
        session: sessions[index + 1] if index + 1 < len(sessions) else None
        for index, session in enumerate(sessions)
    }


def normalize_share_history(raw: pd.DataFrame) -> pd.DataFrame:
    if {"share_date", "total_share_asof"}.issubset(raw.columns):
        out = raw.copy()
        out["share_date"] = pd.to_datetime(out["share_date"], errors="coerce")
        for column in [
            "total_share_asof",
            "float_share_asof",
            "listed_float_share_asof",
        ]:
            if column in out.columns:
                out[column] = numeric_series(out[column])
        if "share_source" not in out.columns:
            out["share_source"] = "cached_normalized_share_history"
        return (
            out.dropna(subset=["share_date", "total_share_asof"])
            .drop_duplicates("share_date", keep="last")
            .sort_values("share_date")
            .reset_index(drop=True)
        )
    if {"变更日期", "总股本"}.issubset(raw.columns):
        out = pd.DataFrame()
        out["share_date"] = pd.to_datetime(raw["变更日期"], errors="coerce")
        out["total_share_asof"] = numeric_series(raw["总股本"])
        if "已上市流通A股" in raw.columns:
            out["float_share_asof"] = numeric_series(raw["已上市流通A股"])
        if "已流通股份" in raw.columns:
            out["listed_float_share_asof"] = numeric_series(raw["已流通股份"])
        out["share_source"] = "stock_zh_a_gbjg_em"
        return (
            out.dropna(subset=["share_date", "total_share_asof"])
            .drop_duplicates("share_date", keep="last")
            .sort_values("share_date")
            .reset_index(drop=True)
        )
    if {"变动日期", "总股本"}.issubset(raw.columns):
        out = pd.DataFrame()
        out["share_date"] = pd.to_datetime(raw["变动日期"], errors="coerce")
        out["total_share_asof"] = numeric_series(raw["总股本"]) * 10_000.0
        if "已流通股份" in raw.columns:
            out["float_share_asof"] = numeric_series(raw["已流通股份"]) * 10_000.0
        if "人民币普通股" in raw.columns:
            out["listed_float_share_asof"] = numeric_series(raw["人民币普通股"]) * 10_000.0
        out["share_source"] = "stock_share_change_cninfo"
        return (
            out.dropna(subset=["share_date", "total_share_asof"])
            .drop_duplicates("share_date", keep="last")
            .sort_values("share_date")
            .reset_index(drop=True)
        )
    raise TopNUniverseBlocked(
        "topn_universe_source_blocked",
        "share history cache has unsupported schema",
    )


def expand_share_asof(share_history: pd.DataFrame, dates: Iterable[str]) -> pd.DataFrame:
    date_frame = pd.DataFrame({"date": pd.to_datetime(list(dates))}).sort_values("date")
    shares = share_history.sort_values("share_date").copy()
    expanded = pd.merge_asof(
        date_frame,
        shares,
        left_on="date",
        right_on="share_date",
        direction="backward",
    )
    expanded["source_asof_date"] = expanded["share_date"].dt.strftime("%Y-%m-%d")
    expanded["date"] = expanded["date"].dt.strftime("%Y-%m-%d")
    return expanded.drop(columns=["share_date"])


def is_active_in_window(row: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> bool:
    listing = pd.to_datetime(row.get("listing_date"), errors="coerce")
    delist = pd.to_datetime(row.get("delist_date"), errors="coerce")
    if pd.isna(listing) or listing > end:
        return False
    if pd.notna(delist) and delist <= start:
        return False
    return True


def build_active_listing_counts(metadata: pd.DataFrame, calendar: list[str]) -> pd.DataFrame:
    dates = pd.to_datetime(pd.Series(calendar))
    rows: list[dict[str, Any]] = []
    for bucket in ALLOWED_BUCKETS:
        diff = np.zeros(len(calendar) + 1, dtype=np.int64)
        bucket_meta = metadata[metadata["board_bucket"] == bucket]
        for item in bucket_meta.itertuples(index=False):
            listing = pd.to_datetime(getattr(item, "listing_date"), errors="coerce")
            delist = pd.to_datetime(getattr(item, "delist_date"), errors="coerce")
            if pd.isna(listing):
                continue
            start_idx = int(np.searchsorted(dates.values, listing.to_datetime64(), side="left"))
            if start_idx >= len(calendar):
                continue
            if pd.isna(delist):
                end_idx = len(calendar)
            else:
                end_idx = int(np.searchsorted(dates.values, delist.to_datetime64(), side="left"))
            if end_idx <= 0 or start_idx >= end_idx:
                continue
            diff[start_idx] += 1
            diff[end_idx] -= 1
        counts = np.cumsum(diff[:-1])
        rows.extend(
            {
                "membership_date": date,
                "board_bucket": bucket,
                "listed_instrument_count": int(count),
            }
            for date, count in zip(calendar, counts)
        )
    return pd.DataFrame(rows)


def load_metadata(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise TopNUniverseBlocked(
            "topn_universe_candidate_panel_blocked",
            f"instrument metadata is missing: {path}",
        )
    metadata = pd.read_csv(path, dtype="string")
    require_columns(
        metadata,
        ["code", "instrument", "exchange", "listing_date", "delist_date", "board_bucket"],
        "instrument_metadata",
    )
    metadata["instrument"] = metadata["instrument"].map(instrument_from_code)
    metadata["ts_code"] = metadata["code"].map(strip_code)
    metadata["board_bucket"] = metadata["instrument"].map(board_bucket)
    metadata = metadata[metadata["board_bucket"].isin(ALLOWED_BUCKETS)].copy()
    metadata = metadata.drop_duplicates("instrument", keep="first")
    return metadata.sort_values("instrument").reset_index(drop=True)


def load_sz_name_changes(path: Path) -> dict[str, pd.DataFrame]:
    if not path.is_file():
        return {}
    raw = pd.read_csv(path, dtype="string")
    rename = {
        "变更日期": "change_date",
        "证券代码": "code",
        "变更前简称": "previous_name",
        "变更后简称": "next_name",
    }
    out = raw.rename(columns=rename).copy()
    required = {"change_date", "code", "previous_name", "next_name"}
    if not required.issubset(out.columns):
        return {}
    out["code"] = out["code"].map(strip_code)
    out["change_date"] = pd.to_datetime(out["change_date"], errors="coerce")
    out = out.dropna(subset=["change_date", "code"])
    return {
        code: group.sort_values("change_date").reset_index(drop=True)
        for code, group in out.groupby("code")
    }


def sh_lifetime_st_flag(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        history = pd.read_csv(path, dtype="string")
    except pd.errors.EmptyDataError:
        return False
    return has_any_st_name_marker(history)


def sz_st_mask_for_dates(dates: pd.Series, changes: pd.DataFrame | None) -> pd.Series:
    if changes is None or changes.empty:
        return pd.Series(False, index=dates.index)
    change_rows = changes.sort_values("change_date").copy()
    base = pd.DataFrame({"date": pd.to_datetime(dates), "_idx": dates.index}).sort_values(
        "date"
    )
    merged = pd.merge_asof(
        base,
        change_rows[["change_date", "previous_name", "next_name"]],
        left_on="date",
        right_on="change_date",
        direction="backward",
    )
    first_previous = str(change_rows.iloc[0]["previous_name"])
    merged["status_name"] = merged["next_name"]
    merged.loc[merged["change_date"].isna(), "status_name"] = first_previous
    merged["is_st"] = merged["status_name"].map(has_st_name_marker).fillna(False)
    return merged.set_index("_idx").sort_index()["is_st"].reindex(dates.index).fillna(False)


def status_source_for_exchange(exchange: str) -> str:
    if exchange == "SH":
        return "stock_info_change_name_lifetime_st_exclusion;daily_bar_presence"
    if exchange == "SZ":
        return "stock_info_sz_change_name_asof;daily_bar_presence"
    return "unsupported_exchange"


def load_raw_daily_frame(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, dtype={"date": "string"})
    require_columns(
        raw,
        ["date", "open", "high", "low", "close", "volume"],
        f"raw_daily:{path.name}",
    )
    out = raw[["date", "open", "high", "low", "close", "volume"]].copy()
    if "money" in raw.columns:
        out["money"] = raw["money"]
    else:
        out["money"] = np.nan
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    for column in ["open", "high", "low", "close", "volume", "money"]:
        out[column] = numeric_series(out[column])
    out = out.dropna(subset=["date", "open", "high", "low", "close", "volume"])
    out = out.drop_duplicates("date", keep="last").sort_values("date")
    return out.reset_index(drop=True)


def build_candidate_panel(
    *,
    metadata: pd.DataFrame,
    calendar: list[str],
    next_trade_date: dict[str, str | None],
    raw_daily_dir: Path,
    market_cap_dir: Path,
    sh_name_history_dir: Path,
    sz_changes_by_code: dict[str, pd.DataFrame],
    candidate_source: str,
    membership_rule_version: str,
) -> tuple[pd.DataFrame, pd.DataFrame, int, int]:
    start = parse_date(calendar[0])
    end = parse_date(calendar[-1])
    calendar_set = set(calendar)
    frames: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []
    source_gap_count = 0
    active_source_gap_count = 0

    for row in metadata.to_dict("records"):
        instrument = row["instrument"]
        raw_path = raw_daily_dir / f"{instrument}.csv"
        share_path = market_cap_dir / f"{instrument}_shares.csv"
        active = is_active_in_window(pd.Series(row), start, end)
        raw_exists = raw_path.is_file()
        share_exists = share_path.is_file()
        if not raw_exists or not share_exists:
            source_gap_count += 1
            if active:
                active_source_gap_count += 1
            audit_rows.append(
                {
                    "instrument": instrument,
                    "board_bucket": row["board_bucket"],
                    "active_in_requested_window": bool(active),
                    "raw_daily_file_exists": bool(raw_exists),
                    "share_history_file_exists": bool(share_exists),
                    "status_file_exists": bool(
                        row["exchange"] == "SZ"
                        or (sh_name_history_dir / f"{instrument}.csv").is_file()
                    ),
                    "raw_rows": 0,
                    "rows_in_resolved_calendar": 0,
                    "missing_share_asof_rows": 0,
                    "eligible_candidate_rows": 0,
                    "first_price_date": "",
                    "last_price_date": "",
                    "market_cap_source": "raw_close_times_total_share_asof",
                    "latest_only": False,
                    "support_state": "missing_active_source" if active else "missing_inactive_source",
                    "notes": "missing raw daily or historical share cache",
                }
            )
            continue

        daily = load_raw_daily_frame(raw_path)
        raw_rows = len(daily)
        daily = daily[daily["date"].isin(calendar_set)].copy()
        if daily.empty:
            audit_rows.append(
                {
                    "instrument": instrument,
                    "board_bucket": row["board_bucket"],
                    "active_in_requested_window": bool(active),
                    "raw_daily_file_exists": True,
                    "share_history_file_exists": True,
                    "status_file_exists": bool(
                        row["exchange"] == "SZ"
                        or (sh_name_history_dir / f"{instrument}.csv").is_file()
                    ),
                    "raw_rows": int(raw_rows),
                    "rows_in_resolved_calendar": 0,
                    "missing_share_asof_rows": 0,
                    "eligible_candidate_rows": 0,
                    "first_price_date": "",
                    "last_price_date": "",
                    "market_cap_source": "raw_close_times_total_share_asof",
                    "latest_only": False,
                    "support_state": "no_rows_in_resolved_calendar",
                    "notes": "",
                }
            )
            continue

        share_history = normalize_share_history(pd.read_csv(share_path, dtype="string"))
        shares = expand_share_asof(share_history, daily["date"])
        panel = daily.merge(shares, on="date", how="left")
        panel["membership_date"] = panel["date"]
        panel["usable_trade_date"] = panel["membership_date"].map(next_trade_date)
        panel["available_time"] = panel["membership_date"] + " close"
        panel["membership_available_time"] = panel["available_time"]
        panel["instrument"] = instrument
        panel["ts_code"] = strip_code(row["code"])
        panel["board_bucket"] = row["board_bucket"]
        panel["raw_unadjusted_close"] = panel["close"]
        panel["total_market_cap_cny"] = (
            panel["raw_unadjusted_close"] * panel["total_share_asof"]
        )
        panel["market_cap_source"] = "raw_close_times_total_share_asof"
        panel["price_source"] = "raw_close"
        panel["share_source"] = panel["share_source"].fillna(
            ";".join(sorted(share_history["share_source"].dropna().unique()))
        )
        panel["source_trade_date"] = panel["date"]
        panel["candidate_universe_source"] = candidate_source
        panel["membership_rule_version"] = membership_rule_version
        panel["is_listed"] = listed_mask(panel, row)

        exchange = str(row["exchange"])
        if exchange == "SH":
            is_st = sh_lifetime_st_flag(sh_name_history_dir / f"{instrument}.csv")
            panel["is_st"] = is_st
        elif exchange == "SZ":
            panel["is_st"] = sz_st_mask_for_dates(
                panel["date"], sz_changes_by_code.get(strip_code(row["code"]))
            )
        else:
            panel["is_st"] = True
        panel["is_suspended"] = False
        panel["status_source"] = status_source_for_exchange(exchange)

        panel = panel.replace([np.inf, -np.inf], np.nan)
        panel = panel.sort_values("membership_date").reset_index(drop=True)
        panel["_observed_sessions_before_usable"] = np.arange(1, len(panel) + 1)

        keep_cols = [
            "membership_date",
            "available_time",
            "membership_available_time",
            "usable_trade_date",
            "instrument",
            "ts_code",
            "board_bucket",
            "is_listed",
            "is_st",
            "is_suspended",
            "raw_unadjusted_close",
            "total_share_asof",
            "total_market_cap_cny",
            "market_cap_source",
            "price_source",
            "share_source",
            "status_source",
            "source_trade_date",
            "source_asof_date",
            "candidate_universe_source",
            "membership_rule_version",
            "_observed_sessions_before_usable",
        ]
        candidate = panel[keep_cols].copy()
        frames.append(candidate)

        listed = bool_series(candidate["is_listed"])
        st = bool_series(candidate["is_st"])
        suspended = bool_series(candidate["is_suspended"])
        finite_cap = np.isfinite(candidate["total_market_cap_cny"]) & (
            candidate["total_market_cap_cny"] > 0
        )
        eligible = listed & ~st & ~suspended & finite_cap
        audit_rows.append(
            {
                "instrument": instrument,
                "board_bucket": row["board_bucket"],
                "active_in_requested_window": bool(active),
                "raw_daily_file_exists": True,
                "share_history_file_exists": True,
                "status_file_exists": bool(
                    exchange == "SZ" or (sh_name_history_dir / f"{instrument}.csv").is_file()
                ),
                "raw_rows": int(raw_rows),
                "rows_in_resolved_calendar": int(len(candidate)),
                "missing_share_asof_rows": int(candidate["total_share_asof"].isna().sum()),
                "eligible_candidate_rows": int(eligible.sum()),
                "first_price_date": str(candidate["membership_date"].min()),
                "last_price_date": str(candidate["membership_date"].max()),
                "market_cap_source": "raw_close_times_total_share_asof",
                "latest_only": False,
                "support_state": "supported",
                "notes": "",
            }
        )

    if not frames:
        raise TopNUniverseBlocked(
            "topn_universe_candidate_panel_blocked",
            "no candidate rows were reconstructed from the cached raw layer",
        )
    candidate_panel = pd.concat(frames, ignore_index=True)
    return (
        candidate_panel,
        pd.DataFrame(audit_rows).sort_values("instrument").reset_index(drop=True),
        source_gap_count,
        active_source_gap_count,
    )


def listed_mask(panel: pd.DataFrame, row: dict[str, Any]) -> pd.Series:
    dates = pd.to_datetime(panel["date"], errors="coerce")
    listing = pd.to_datetime(row.get("listing_date"), errors="coerce")
    delist = pd.to_datetime(row.get("delist_date"), errors="coerce")
    mask = dates >= listing if pd.notna(listing) else pd.Series(False, index=panel.index)
    if pd.notna(delist):
        mask = mask & (dates < delist)
    return mask.fillna(False)


def guard_candidate_source(candidate: pd.DataFrame) -> None:
    if "candidate_universe_source" not in candidate.columns:
        raise TopNUniverseBlocked(
            "topn_universe_candidate_panel_blocked",
            "candidate panel does not declare candidate_universe_source",
        )
    sources = set(candidate["candidate_universe_source"].dropna().astype(str).unique())
    if sources != {"full_board_candidate_panel"}:
        raise TopNUniverseBlocked(
            "topn_universe_candidate_panel_blocked",
            f"ranking source must be full_board_candidate_panel, got {sorted(sources)}",
        )


def select_topn_membership(
    candidate: pd.DataFrame,
    *,
    quotas: dict[str, int],
    minimum_history_sessions: int,
    rank_rule_version: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    guard_candidate_source(candidate)
    require_columns(
        candidate,
        [
            "membership_date",
            "instrument",
            "board_bucket",
            "is_listed",
            "is_st",
            "is_suspended",
            "total_market_cap_cny",
            "raw_unadjusted_close",
            "total_share_asof",
        ],
        "candidate_panel",
    )
    panel = candidate.copy()
    panel["is_listed"] = bool_series(panel["is_listed"])
    panel["is_st"] = bool_series(panel["is_st"])
    panel["is_suspended"] = bool_series(panel["is_suspended"])
    panel["total_market_cap_cny"] = pd.to_numeric(
        panel["total_market_cap_cny"], errors="coerce"
    )
    panel["raw_unadjusted_close"] = pd.to_numeric(
        panel["raw_unadjusted_close"], errors="coerce"
    )
    panel["total_share_asof"] = pd.to_numeric(panel["total_share_asof"], errors="coerce")
    panel["board_quota"] = panel["board_bucket"].map(quotas)
    finite_cap = np.isfinite(panel["total_market_cap_cny"]) & (
        panel["total_market_cap_cny"] > 0
    )
    finite_close = np.isfinite(panel["raw_unadjusted_close"]) & (
        panel["raw_unadjusted_close"] > 0
    )
    finite_share = np.isfinite(panel["total_share_asof"]) & (
        panel["total_share_asof"] > 0
    )
    eligible = (
        panel["board_bucket"].isin(quotas)
        & panel["is_listed"]
        & ~panel["is_st"]
        & ~panel["is_suspended"]
        & finite_cap
        & finite_close
        & finite_share
    )
    panel = panel[eligible].copy()
    if panel.empty:
        raise TopNUniverseBlocked(
            "topn_universe_candidate_panel_blocked",
            "candidate panel produced no eligible rows after PIT filters",
        )

    panel = panel.sort_values(
        ["membership_date", "board_bucket", "total_market_cap_cny", "instrument"],
        ascending=[True, True, False, True],
    ).reset_index(drop=True)
    panel["board_rank_by_market_cap"] = (
        panel.groupby(["membership_date", "board_bucket"]).cumcount() + 1
    )
    membership = panel[panel["board_rank_by_market_cap"] <= panel["board_quota"]].copy()

    group_counts = (
        panel.groupby(["membership_date", "board_bucket"], dropna=False)
        .agg(eligible_count=("instrument", "nunique"), board_quota=("board_quota", "first"))
        .reset_index()
    )
    kept_counts = (
        membership.groupby(["membership_date", "board_bucket"], dropna=False)
        .agg(kept_count=("instrument", "nunique"))
        .reset_index()
    )
    quota_fill = group_counts.merge(
        kept_counts, on=["membership_date", "board_bucket"], how="left"
    )
    quota_fill["kept_count"] = quota_fill["kept_count"].fillna(0).astype(int)
    quota_fill["quota_fill_rate"] = quota_fill["kept_count"] / quota_fill["board_quota"]
    quota_fill["quota_shortfall_count"] = (
        quota_fill["board_quota"] - quota_fill["kept_count"]
    ).clip(lower=0)
    quota_fill["quota_shortfall_reason"] = np.where(
        quota_fill["quota_shortfall_count"] > 0,
        "insufficient_eligible_names",
        "",
    )
    cutoffs = (
        membership.groupby(["membership_date", "board_bucket"], dropna=False)
        .agg(rank_cutoff_market_cap_cny=("total_market_cap_cny", "min"))
        .reset_index()
    )
    quota_fill = quota_fill.merge(cutoffs, on=["membership_date", "board_bucket"], how="left")
    membership = membership.merge(
        quota_fill[
            [
                "membership_date",
                "board_bucket",
                "quota_fill_rate",
                "quota_shortfall_count",
                "quota_shortfall_reason",
                "rank_cutoff_market_cap_cny",
            ]
        ],
        on=["membership_date", "board_bucket"],
        how="left",
    )
    membership["rank_rule_version"] = rank_rule_version
    membership["minimum_history_sessions"] = minimum_history_sessions
    membership["history_observed_sessions_before_usable_date"] = pd.to_numeric(
        membership.get("_observed_sessions_before_usable", np.nan), errors="coerce"
    ).astype("Int64")
    membership["history_ready_240d_flag"] = (
        membership["history_observed_sessions_before_usable_date"]
        >= minimum_history_sessions
    )
    membership["history_ready_missing_reason"] = np.where(
        membership["history_ready_240d_flag"], "", "insufficient_history"
    )
    membership = membership.sort_values(["membership_date", "instrument"]).reset_index(drop=True)
    return membership[MEMBERSHIP_COLUMNS], quota_fill.sort_values(
        ["membership_date", "board_bucket"]
    ).reset_index(drop=True)


def shift_membership_to_executable(membership: pd.DataFrame) -> pd.DataFrame:
    require_columns(
        membership,
        ["membership_date", "usable_trade_date", "instrument"],
        "membership_daily",
    )
    executable = membership.dropna(subset=["usable_trade_date"]).copy()
    executable["source_membership_date"] = executable["membership_date"]
    bad_clock = pd.to_datetime(executable["source_membership_date"]) >= pd.to_datetime(
        executable["usable_trade_date"]
    )
    if bad_clock.any():
        raise TopNUniverseBlocked(
            "topn_universe_pit_clock_blocked",
            "membership_date must be strictly before usable_trade_date",
        )
    if executable.duplicated(["usable_trade_date", "instrument"]).any():
        raise TopNUniverseBlocked(
            "topn_universe_pit_clock_blocked",
            "duplicate executable key usable_trade_date,instrument",
        )
    return executable[EXECUTABLE_COLUMNS].sort_values(
        ["usable_trade_date", "instrument"]
    ).reset_index(drop=True)


def compress_executable_intervals(executable: pd.DataFrame, calendar: Iterable[str]) -> pd.DataFrame:
    rank = {session: index for index, session in enumerate(calendar)}
    dates = executable[["instrument", "usable_trade_date"]].copy()
    dates["calendar_rank"] = dates["usable_trade_date"].map(rank)
    dates = dates.dropna(subset=["calendar_rank"]).copy()
    rows: list[dict[str, Any]] = []
    if dates.empty:
        return pd.DataFrame(columns=["instrument", "start_datetime", "end_datetime", "session_count"])
    for instrument, group in dates.sort_values(["instrument", "calendar_rank"]).groupby(
        "instrument"
    ):
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


def write_qlib_intervals(intervals: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in intervals.sort_values(["instrument", "start_datetime"]).itertuples(index=False):
            handle.write(f"{row.instrument}\t{row.start_datetime}\t{row.end_datetime}\n")


def build_daily_counts(membership: pd.DataFrame) -> pd.DataFrame:
    usable = (
        membership.groupby("membership_date", dropna=False)
        .agg(usable_trade_date=("usable_trade_date", "first"))
        .reset_index()
    )
    board = (
        membership.groupby(["membership_date", "board_bucket"], dropna=False)
        .agg(member_count=("instrument", "nunique"))
        .reset_index()
    )
    pivot = board.pivot_table(
        index="membership_date",
        columns="board_bucket",
        values="member_count",
        fill_value=0,
        aggfunc="sum",
    ).reset_index()
    for bucket in ALLOWED_BUCKETS:
        if bucket not in pivot.columns:
            pivot[bucket] = 0
    pivot["member_count"] = pivot["main_board"] + pivot["chinext"]
    pivot = usable.merge(pivot, on="membership_date", how="right")
    return pivot.rename(
        columns={
            "main_board": "main_board_count",
            "chinext": "chinext_count",
        }
    )[
        [
            "membership_date",
            "usable_trade_date",
            "member_count",
            "main_board_count",
            "chinext_count",
        ]
    ].sort_values("membership_date").reset_index(drop=True)


def build_board_counts(membership: pd.DataFrame) -> pd.DataFrame:
    return (
        membership.groupby(["membership_date", "usable_trade_date", "board_bucket"], dropna=False)
        .agg(member_count=("instrument", "nunique"))
        .reset_index()
        .sort_values(["membership_date", "board_bucket"])
    )


def build_status_exclusion_audit(
    candidate: pd.DataFrame, active_listing_counts: pd.DataFrame
) -> pd.DataFrame:
    panel = candidate.copy()
    panel["is_listed"] = bool_series(panel["is_listed"])
    panel["is_st"] = bool_series(panel["is_st"])
    panel["is_suspended"] = bool_series(panel["is_suspended"])
    finite_cap = np.isfinite(pd.to_numeric(panel["total_market_cap_cny"], errors="coerce")) & (
        pd.to_numeric(panel["total_market_cap_cny"], errors="coerce") > 0
    )
    grouped = []
    for keys, group in panel.groupby(["membership_date", "board_bucket"], dropna=False):
        listed = bool_series(group["is_listed"])
        st = bool_series(group["is_st"])
        suspended = bool_series(group["is_suspended"])
        cap = np.isfinite(pd.to_numeric(group["total_market_cap_cny"], errors="coerce")) & (
            pd.to_numeric(group["total_market_cap_cny"], errors="coerce") > 0
        )
        grouped.append(
            {
                "membership_date": keys[0],
                "board_bucket": keys[1],
                "candidate_with_daily_bar_count": int(len(group)),
                "listed_with_daily_bar_count": int(listed.sum()),
                "excluded_not_listed_count": int((~listed).sum()),
                "excluded_st_count": int((listed & st).sum()),
                "excluded_suspended_count": int((listed & ~st & suspended).sum()),
                "excluded_missing_market_cap_count": int((listed & ~st & ~suspended & ~cap).sum()),
                "eligible_count": int((listed & ~st & ~suspended & cap).sum()),
                "status_source": ";".join(sorted(group["status_source"].dropna().unique())),
            }
        )
    out = pd.DataFrame(grouped)
    out = active_listing_counts.merge(
        out, on=["membership_date", "board_bucket"], how="left"
    )
    count_cols = [
        "candidate_with_daily_bar_count",
        "listed_with_daily_bar_count",
        "excluded_not_listed_count",
        "excluded_st_count",
        "excluded_suspended_count",
        "excluded_missing_market_cap_count",
        "eligible_count",
    ]
    for column in count_cols:
        out[column] = out[column].fillna(0).astype(int)
    out["excluded_missing_daily_bar_count"] = (
        out["listed_instrument_count"] - out["listed_with_daily_bar_count"]
    ).clip(lower=0)
    out["status_source"] = out["status_source"].fillna("")
    return out[
        [
            "membership_date",
            "board_bucket",
            "listed_instrument_count",
            "candidate_with_daily_bar_count",
            "excluded_missing_daily_bar_count",
            "excluded_not_listed_count",
            "excluded_st_count",
            "excluded_suspended_count",
            "excluded_missing_market_cap_count",
            "eligible_count",
            "status_source",
        ]
    ].sort_values(["membership_date", "board_bucket"]).reset_index(drop=True)


def build_rank_cutoff_audit(quota_fill: pd.DataFrame) -> pd.DataFrame:
    out = quota_fill.copy()
    out["year"] = out["membership_date"].astype(str).str[:4].astype(int)
    return out[
        [
            "membership_date",
            "year",
            "board_bucket",
            "eligible_count",
            "kept_count",
            "board_quota",
            "quota_fill_rate",
            "rank_cutoff_market_cap_cny",
        ]
    ].sort_values(["membership_date", "board_bucket"]).reset_index(drop=True)


def build_history_coverage_audit(membership: pd.DataFrame) -> pd.DataFrame:
    out = membership.copy()
    out["year"] = out["membership_date"].astype(str).str[:4].astype(int)
    grouped = (
        out.groupby(["year", "board_bucket"], dropna=False)
        .agg(
            member_rows=("instrument", "size"),
            unique_instruments=("instrument", "nunique"),
            history_ready_240d_count=("history_ready_240d_flag", "sum"),
            history_observed_sessions_mean=(
                "history_observed_sessions_before_usable_date",
                "mean",
            ),
            history_observed_sessions_min=(
                "history_observed_sessions_before_usable_date",
                "min",
            ),
        )
        .reset_index()
    )
    grouped["history_ready_240d_rate"] = (
        grouped["history_ready_240d_count"] / grouped["member_rows"]
    )
    return grouped.sort_values(["year", "board_bucket"]).reset_index(drop=True)


def build_fixed_cap_overlap_audit(
    topn_membership: pd.DataFrame, fixed_cap_membership: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    require_columns(
        fixed_cap_membership,
        ["membership_date", "instrument", "board_bucket"],
        "fixed_cap_membership",
    )
    topn = topn_membership[["membership_date", "instrument", "board_bucket"]].copy()
    topn["in_topn"] = True
    fixed = fixed_cap_membership[["membership_date", "instrument", "board_bucket"]].copy()
    fixed["in_fixed_cap"] = True
    merged = topn.merge(
        fixed,
        on=["membership_date", "instrument", "board_bucket"],
        how="outer",
    )
    merged["in_topn"] = merged["in_topn"].where(merged["in_topn"].notna(), False).astype(bool)
    merged["in_fixed_cap"] = (
        merged["in_fixed_cap"].where(merged["in_fixed_cap"].notna(), False).astype(bool)
    )
    rows: list[dict[str, Any]] = []
    for keys, group in merged.groupby(["membership_date", "board_bucket"], dropna=False):
        topn_count = int(group["in_topn"].sum())
        fixed_count = int(group["in_fixed_cap"].sum())
        intersection = int((group["in_topn"] & group["in_fixed_cap"]).sum())
        union = int((group["in_topn"] | group["in_fixed_cap"]).sum())
        rows.append(
            {
                "membership_date": keys[0],
                "year": int(str(keys[0])[:4]),
                "board_bucket": keys[1],
                "topn_count": topn_count,
                "fixed_cap_count": fixed_count,
                "intersection_count": intersection,
                "topn_only_count": topn_count - intersection,
                "fixed_cap_only_count": fixed_count - intersection,
                "jaccard_overlap": intersection / union if union else np.nan,
            }
        )
    overlap = pd.DataFrame(rows).sort_values(["membership_date", "board_bucket"])
    diff = overlap.copy()
    diff["topn_only_share_of_topn"] = np.where(
        diff["topn_count"] > 0, diff["topn_only_count"] / diff["topn_count"], np.nan
    )
    diff["fixed_cap_only_share_of_fixed_cap"] = np.where(
        diff["fixed_cap_count"] > 0,
        diff["fixed_cap_only_count"] / diff["fixed_cap_count"],
        np.nan,
    )
    return overlap.reset_index(drop=True), diff.reset_index(drop=True)


def build_yearly_summary(
    daily_counts: pd.DataFrame,
    quota_fill: pd.DataFrame,
    history_audit: pd.DataFrame,
) -> pd.DataFrame:
    daily = daily_counts.copy()
    daily["year"] = daily["membership_date"].astype(str).str[:4].astype(int)
    yearly = (
        daily.groupby("year")
        .agg(
            trading_days=("membership_date", "nunique"),
            avg_daily_member_count=("member_count", "mean"),
            min_daily_member_count=("member_count", "min"),
            max_daily_member_count=("member_count", "max"),
            instrument_days=("member_count", "sum"),
            avg_main_board_count=("main_board_count", "mean"),
            avg_chinext_count=("chinext_count", "mean"),
        )
        .reset_index()
    )
    yearly["universe_years_252"] = yearly["instrument_days"] / 252.0
    quota = quota_fill.copy()
    quota["year"] = quota["membership_date"].astype(str).str[:4].astype(int)
    quota_pivot = quota.pivot_table(
        index="year",
        columns="board_bucket",
        values="quota_fill_rate",
        aggfunc="mean",
    ).reset_index()
    quota_pivot = quota_pivot.rename(
        columns={
            "main_board": "main_board_quota_fill_rate_mean",
            "chinext": "chinext_quota_fill_rate_mean",
        }
    )
    hist = (
        history_audit.groupby("year")
        .agg(
            history_ready_240d_count=("history_ready_240d_count", "sum"),
            member_rows=("member_rows", "sum"),
        )
        .reset_index()
    )
    hist["history_ready_240d_rate"] = hist["history_ready_240d_count"] / hist[
        "member_rows"
    ]
    out = yearly.merge(quota_pivot, on="year", how="left").merge(
        hist[["year", "history_ready_240d_rate"]], on="year", how="left"
    )
    for column in [
        "main_board_quota_fill_rate_mean",
        "chinext_quota_fill_rate_mean",
        "history_ready_240d_rate",
    ]:
        if column not in out.columns:
            out[column] = np.nan
    return out[
        [
            "year",
            "trading_days",
            "avg_daily_member_count",
            "min_daily_member_count",
            "max_daily_member_count",
            "instrument_days",
            "universe_years_252",
            "avg_main_board_count",
            "avg_chinext_count",
            "main_board_quota_fill_rate_mean",
            "chinext_quota_fill_rate_mean",
            "history_ready_240d_rate",
        ]
    ].sort_values("year").reset_index(drop=True)


def validate_outputs(
    *,
    membership: pd.DataFrame,
    executable: pd.DataFrame,
    gate_summary: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    if membership.duplicated(["membership_date", "instrument"]).any():
        failures.append("duplicate_membership_key")
    if executable.duplicated(["usable_trade_date", "instrument"]).any():
        failures.append("duplicate_executable_key")
    if not set(membership["board_bucket"]).issubset(set(ALLOWED_BUCKETS)):
        failures.append("outside_allowed_board_bucket")
    if not executable.empty:
        bad_clock = pd.to_datetime(executable["source_membership_date"]) >= pd.to_datetime(
            executable["usable_trade_date"]
        )
        if bad_clock.any():
            failures.append("membership_date_not_before_usable_trade_date")
    daily_total = membership.groupby("membership_date")["instrument"].nunique()
    if (daily_total > int(validation["max_total_daily_members"])).any():
        failures.append("daily_member_count_above_500")
    board = (
        membership.groupby(["membership_date", "board_bucket"])["instrument"]
        .nunique()
        .reset_index(name="count")
    )
    if (
        board.loc[board["board_bucket"] == "main_board", "count"]
        > int(validation["max_main_board_daily_members"])
    ).any():
        failures.append("main_board_count_above_400")
    if (
        board.loc[board["board_bucket"] == "chinext", "count"]
        > int(validation["max_chinext_daily_members"])
    ).any():
        failures.append("chinext_count_above_100")
    disallowed = validation.get("disallowed_market_cap_sources", [])
    source_text = "|".join(sorted(membership["market_cap_source"].dropna().astype(str).unique()))
    for token in disallowed:
        if token in source_text:
            failures.append(f"disallowed_market_cap_source:{token}")
    if gate_summary.get("candidate_panel_source") != "full_board_candidate_panel":
        failures.append("ranking_source_not_full_board_candidate_panel")
    if validation.get("block_on_active_source_gaps", True) and gate_summary.get(
        "active_source_gap_count", 0
    ):
        failures.append("active_source_gaps")
    gate_summary = dict(gate_summary)
    gate_summary["validation_failures"] = failures
    gate_summary["validation_passed"] = not failures
    return gate_summary


def build_all_outputs(
    *,
    build_inputs: BuildInputs,
    fixed_cap_membership: pd.DataFrame,
    quotas: dict[str, int],
    minimum_history_sessions: int,
    rank_rule_version: str,
    validation: dict[str, Any],
) -> TopNResult:
    membership, quota_fill = select_topn_membership(
        build_inputs.candidate,
        quotas=quotas,
        minimum_history_sessions=minimum_history_sessions,
        rank_rule_version=rank_rule_version,
    )
    executable = shift_membership_to_executable(membership)
    intervals = compress_executable_intervals(executable, build_inputs.calendar)
    daily_counts = build_daily_counts(membership)
    board_counts = build_board_counts(membership)
    rank_cutoff_audit = build_rank_cutoff_audit(quota_fill)
    status_exclusion_audit = build_status_exclusion_audit(
        build_inputs.candidate, build_inputs.active_listing_counts
    )
    history_coverage_audit = build_history_coverage_audit(membership)
    overlap, diff = build_fixed_cap_overlap_audit(membership, fixed_cap_membership)
    yearly_summary = build_yearly_summary(daily_counts, quota_fill, history_coverage_audit)
    gate_summary = {
        "candidate_panel_source": "full_board_candidate_panel",
        "source_gap_count": build_inputs.source_gap_count,
        "active_source_gap_count": build_inputs.active_source_gap_count,
        "membership_rows": int(len(membership)),
        "executable_rows": int(len(executable)),
        "interval_rows": int(len(intervals)),
        "resolved_start_trading_date": build_inputs.calendar[0],
        "resolved_end_trading_date": build_inputs.calendar[-1],
        "trading_session_count": int(len(build_inputs.calendar)),
        "max_daily_member_count": int(daily_counts["member_count"].max()),
        "max_main_board_count": int(daily_counts["main_board_count"].max()),
        "max_chinext_count": int(daily_counts["chinext_count"].max()),
        "avg_total_quota_fill_rate": float(
            quota_fill["quota_fill_rate"].mean()
        ),
        "history_ready_240d_rate": float(
            membership["history_ready_240d_flag"].mean()
        ),
    }
    gate_summary = validate_outputs(
        membership=membership,
        executable=executable,
        gate_summary=gate_summary,
        validation=validation,
    )
    return TopNResult(
        membership=membership,
        executable=executable,
        intervals=intervals,
        daily_counts=daily_counts,
        board_counts=board_counts,
        yearly_summary=yearly_summary,
        quota_fill_audit=quota_fill,
        rank_cutoff_audit=rank_cutoff_audit,
        status_exclusion_audit=status_exclusion_audit,
        history_coverage_audit=history_coverage_audit,
        fixed_cap_overlap_audit=overlap,
        topn_only_vs_fixed_cap_only_audit=diff,
        gate_summary=gate_summary,
    )


def decision_from_gates(gate_summary: dict[str, Any]) -> str:
    failures = set(gate_summary.get("validation_failures", []))
    if not failures:
        return "topn_universe_supported"
    if "active_source_gaps" in failures:
        return "topn_universe_candidate_panel_blocked"
    if any("disallowed_market_cap_source" in item for item in failures):
        return "topn_universe_source_blocked"
    if any("clock" in item or "usable" in item for item in failures):
        return "topn_universe_pit_clock_blocked"
    return "topn_universe_source_blocked"


def write_report(
    *,
    path: Path,
    decision: str,
    result: TopNResult,
    source_audit: pd.DataFrame,
    input_hashes: dict[str, str | None],
    upstream_manifest_hash: str | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    yearly = result.yearly_summary.copy()
    quota = result.quota_fill_audit.copy()
    overlap = result.fixed_cap_overlap_audit.copy()
    status = result.status_exclusion_audit.copy()
    history = result.history_coverage_audit.copy()
    active_gaps = int(result.gate_summary.get("active_source_gap_count", 0))
    quota_summary = (
        quota.groupby("board_bucket")
        .agg(
            avg_fill_rate=("quota_fill_rate", "mean"),
            min_fill_rate=("quota_fill_rate", "min"),
            avg_eligible_count=("eligible_count", "mean"),
            avg_kept_count=("kept_count", "mean"),
        )
        .reset_index()
    )
    cutoff_summary = (
        result.rank_cutoff_audit.groupby("board_bucket")
        .agg(
            cutoff_min=("rank_cutoff_market_cap_cny", "min"),
            cutoff_median=("rank_cutoff_market_cap_cny", "median"),
            cutoff_max=("rank_cutoff_market_cap_cny", "max"),
        )
        .reset_index()
    )
    overlap_summary = (
        overlap.groupby("board_bucket")
        .agg(
            topn_count_avg=("topn_count", "mean"),
            fixed_cap_count_avg=("fixed_cap_count", "mean"),
            intersection_avg=("intersection_count", "mean"),
            topn_only_avg=("topn_only_count", "mean"),
            fixed_cap_only_avg=("fixed_cap_only_count", "mean"),
            jaccard_avg=("jaccard_overlap", "mean"),
        )
        .reset_index()
    )
    exclusion_summary = (
        status.groupby("board_bucket")
        .agg(
            missing_daily_bar_avg=("excluded_missing_daily_bar_count", "mean"),
            st_excluded_avg=("excluded_st_count", "mean"),
            suspended_excluded_avg=("excluded_suspended_count", "mean"),
            missing_market_cap_avg=("excluded_missing_market_cap_count", "mean"),
        )
        .reset_index()
    )
    source_summary = (
        source_audit.groupby("support_state")
        .agg(instrument_count=("instrument", "nunique"))
        .reset_index()
    )
    lines = [
        "# PIT Top-N 400/100 Universe Report",
        "",
        "## Final decision",
        "",
        f"- Decision: `{decision}`",
        f"- Validation passed: `{result.gate_summary.get('validation_passed')}`",
        f"- Active source gap count: `{active_gaps}`",
        "- This experiment does not rerun 02 reverse lifecycle profile and does not produce a target episode denominator.",
        "- Next step: rerun 02 reverse lifecycle profile on this universe only after the manifest decision is supported.",
        "",
        "## Input source / manifest / hash audit",
        "",
        f"- Upstream 01 manifest hash: `{upstream_manifest_hash}`",
    ]
    for key, value in sorted(input_hashes.items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Universe rule summary",
            "",
            "- Main board: daily PIT total market cap rank <= 400.",
            "- ChiNext: daily PIT total market cap rank <= 100.",
            "- Ranking field: raw unadjusted close at membership date close times historical total share as-of.",
            "- Deterministic tie-break: total_market_cap_cny desc, instrument asc.",
            "- PIT clock: membership_date close is shifted to the next usable_trade_date.",
            "- History readiness is diagnostic only; it is not a membership eligibility gate.",
            "",
            "## Yearly universe summary",
            "",
            markdown_table(yearly),
            "",
            "## Quota fill audit",
            "",
            markdown_table(quota_summary),
            "",
            "## Rank cutoff market cap distribution",
            "",
            markdown_table(cutoff_summary),
            "",
            "## Fixed-cap overlap",
            "",
            markdown_table(overlap_summary),
            "",
            "## History and exclusions",
            "",
            markdown_table(history),
            "",
            markdown_table(exclusion_summary),
            "",
            "## Source coverage",
            "",
            markdown_table(source_summary),
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_empty_"
    rendered = df.copy()
    for column in rendered.columns:
        if pd.api.types.is_float_dtype(rendered[column]):
            rendered[column] = rendered[column].map(
                lambda value: "" if pd.isna(value) else f"{value:.6g}"
            )
    headers = [str(column) for column in rendered.columns]
    rows = rendered.astype("string").fillna("").values.tolist()
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


def write_manifest(
    *,
    manifest_path: Path,
    config_path: Path,
    config: dict[str, Any],
    project_root: Path,
    decision: str,
    input_paths: dict[str, Path],
    output_paths: dict[str, Path],
    upstream_01_manifest_hash: str | None,
    upstream_01_git_revision: str | None,
    gate_summary: dict[str, Any],
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    input_hashes = {
        key: file_sha256(path) if path.is_file() else None
        for key, path in input_paths.items()
    }
    output_hashes = {
        key: file_sha256(path)
        for key, path in output_paths.items()
        if path.is_file() and path != manifest_path
    }
    manifest = {
        "experiment_name": config["experiment"]["name"],
        "source_git_revision": git_revision(project_root),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "command": sys.argv,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "config_path": str(config_path),
        "config_hash": stable_hash(config),
        "config_file_hash": file_sha256(config_path) if config_path.is_file() else None,
        "input_paths": {key: str(path) for key, path in input_paths.items()},
        "input_hashes": input_hashes,
        "output_paths": {key: str(path) for key, path in output_paths.items()},
        "output_hashes": output_hashes,
        "upstream_01_manifest_hash": upstream_01_manifest_hash,
        "upstream_01_git_revision": upstream_01_git_revision,
        "requested_start_date": config["date_range"]["requested_start_date"],
        "requested_end_date": config["date_range"]["requested_end_date"],
        "resolved_start_trading_date": gate_summary.get("resolved_start_trading_date"),
        "resolved_end_trading_date": gate_summary.get("resolved_end_trading_date"),
        "trading_session_count": gate_summary.get("trading_session_count"),
        "calendar_source": "data/raw/akshare/status/trading_calendar.csv",
        "rank_rule_version": config["universe"]["rank_rule_version"],
        "quota_main_board": config["universe"]["quotas"]["main_board"],
        "quota_chinext": config["universe"]["quotas"]["chinext"],
        "minimum_history_sessions": config["universe"]["minimum_history_sessions"],
        "candidate_panel_source": config["universe"]["candidate_panel_source"],
        "decision": decision,
        "gate_summary": gate_summary,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def stable_hash(value: Any) -> str:
    import hashlib

    payload = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
