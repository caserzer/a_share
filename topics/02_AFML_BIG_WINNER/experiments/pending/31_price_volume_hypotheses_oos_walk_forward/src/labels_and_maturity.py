"""Vectorized EP30-compatible price inference; all unknown endpoints stay unknown."""
from __future__ import annotations

import numpy as np
import pandas as pd


def range_extreme(values, left, right, maximize=True):
    """Inclusive/exclusive RMQ using sparse tables; also works with empty intervals."""
    values = np.asarray(values, float)
    n = len(values)
    fill = -np.inf if maximize else np.inf
    table = [np.where(np.isfinite(values), values, fill)]
    op = np.maximum if maximize else np.minimum
    width = 1
    while width * 2 <= n:
        table.append(op(table[-1][:-width], table[-1][width:]))
        width *= 2
    result = np.full(len(left), np.nan)
    length = np.asarray(right) - np.asarray(left)
    for k in range(len(table)):
        mask = (length >= 2**k) & (length < 2**(k+1))
        if mask.any():
            result[mask] = op(table[k][left[mask]], table[k][right[mask] - 2**k])
    return result


def infer_labels(bars, days, origins, horizon, delist_date=pd.NaT):
    """Independent rederivation reconciled with EP30 monthly values and timings."""
    days, origins = pd.DatetimeIndex(days), pd.DatetimeIndex(origins)
    b = bars.sort_values("date").reset_index(drop=True)
    if b.date.duplicated().any():
        raise ValueError("duplicate label prices")
    rawopen = pd.to_numeric(b.open, errors="coerce").to_numpy(float)
    positive = np.isfinite(rawopen) & (rawopen > 0) & pd.to_numeric(b.volume, errors="coerce").gt(0).to_numpy() & b.date.isin(days).to_numpy()
    if "vendor_trade_status" in b:
        positive &= ~pd.to_numeric(b.vendor_trade_status, errors="coerce").eq(0).to_numpy()
    trades = b[positive].reset_index(drop=True)
    td = pd.DatetimeIndex(trades.date)
    oi = days.searchsorted(origins)
    target_i = days.searchsorted(origins + pd.DateOffset(months=6)) if horizon == "6_calendar_months" else oi + int(horizon)
    nt = len(trades)
    target_valid = target_i < len(days)
    target = np.full(len(origins), np.datetime64("NaT"), dtype="datetime64[ns]")
    target[target_valid] = days.to_numpy()[target_i[target_valid]]
    entry_i = td.searchsorted(origins, side="right")
    exit_i = np.maximum(td.searchsorted(target), entry_i + 1)
    result = pd.DataFrame(dict(date=origins, target_session=target, status="UNKNOWN", reason="MISSING_OBSERVED_ENTRY_OPEN",
                               entry_date=pd.NaT, exit_date=pd.NaT, mature_at=pd.NaT, value=np.nan,
                               raw_price_return=np.nan, mfe=np.nan, mae=np.nan, path_status="UNKNOWN",
                               entry_delay_sessions=np.nan, exit_delay_sessions=np.nan))
    result.loc[~target_valid, ["status", "reason"]] = ["CENSORED", "TARGET_BEYOND_VERIFIED_CALENDAR"]
    terminal = target_valid & pd.notna(delist_date) & (pd.to_datetime(target) >= pd.Timestamp(delist_date))
    result.loc[terminal, "reason"] = "DELISTING_TERMINAL_VALUE_UNOBSERVED"
    if not nt:
        return result
    e, x = np.minimum(entry_i, nt-1), np.minimum(exit_i, nt-1)
    entry_dates, exit_dates = td.to_numpy()[e], td.to_numpy()[x]
    entry_ok = target_valid & ~terminal & (entry_i < nt)
    result.loc[entry_ok, "entry_date"] = entry_dates[entry_ok]
    result.loc[entry_ok, "entry_delay_sessions"] = days.get_indexer(td)[e[entry_ok]] - oi[entry_ok] - 1
    too_late = entry_ok & (entry_dates >= target)
    result.loc[too_late, "reason"] = "ENTRY_NOT_BEFORE_TARGET"
    candidate = entry_ok & ~too_late & (exit_i < nt)
    result.loc[entry_ok & ~too_late & ~candidate, "reason"] = "MISSING_OBSERVED_EXIT_OPEN"
    result.loc[candidate, "exit_date"] = exit_dates[candidate]
    result.loc[candidate, "exit_delay_sessions"] = days.get_indexer(td)[x[candidate]] - target_i[candidate]
    op = pd.to_numeric(trades.qfq_open, errors="coerce").to_numpy(float)
    ro = pd.to_numeric(trades.open, errors="coerce").to_numpy(float)
    conflicts = trades.get("open_conflict", pd.Series(False, index=trades.index)).fillna(False).to_numpy(bool)
    chain = trades.factor_chain_id.to_numpy()
    terminal_exit = candidate & pd.notna(delist_date) & ((entry_dates >= pd.Timestamp(delist_date)) | (exit_dates >= pd.Timestamp(delist_date)))
    badconflict = candidate & ~terminal_exit & (conflicts[e] | conflicts[x])
    badfactor = candidate & ~terminal_exit & ~badconflict & (~np.isfinite(op[e]) | ~np.isfinite(op[x]) | (op[e] <= 0) | (op[x] <= 0))
    badchain = candidate & ~terminal_exit & ~badconflict & ~badfactor & (chain[e] != chain[x])
    for mask, reason in [(terminal_exit, "DELISTING_TERMINAL_VALUE_UNOBSERVED"), (badconflict, "UNRESOLVED_ENDPOINT_OPEN_CONFLICT"),
                         (badfactor, "MISSING_QFQ_ENDPOINT_FACTOR"), (badchain, "UNRECONCILED_CODE_CHANGE_FACTOR_SCALE")]:
        result.loc[mask, "reason"] = reason
    known = candidate & ~terminal_exit & ~badconflict & ~badfactor & ~badchain
    rawknown = candidate & ~terminal_exit & ~badconflict
    result.loc[rawknown, "raw_price_return"] = ro[x[rawknown]] / ro[e[rawknown]] - 1
    result.loc[known, "value"] = op[x[known]] / op[e[known]] - 1
    result.loc[known, ["status", "reason"]] = ["KNOWN_INFERRED", "QFQ_OBSERVED_PRICE_CHANGE_EXECUTION_ASSUMED"]
    result.loc[known, "mature_at"] = pd.to_datetime(exit_dates[known]) + pd.Timedelta(hours=9, minutes=30)
    # Path metrics use observed close marks including zero and exit-open endpoint.
    close = pd.to_numeric(b.qfq_close, errors="coerce").to_numpy(float)
    valid = np.isfinite(close) & (close > 0) & b.date.isin(days).to_numpy()
    valid &= ~b.get("close_conflict", pd.Series(False, index=b.index)).fillna(False).to_numpy(bool)
    bi = np.flatnonzero(positive)
    left, right = bi[e], bi[x]
    count = np.r_[0, np.cumsum(valid)]
    expected = days.get_indexer(td)[x] - days.get_indexer(td)[e]
    complete = known & ((count[right] - count[left]) == expected)
    # Reject paths crossing an unresolved chain even if endpoints happen to match.
    changes = np.r_[0, np.cumsum(b.factor_chain_id.ne(b.factor_chain_id.shift()).to_numpy())]
    complete &= changes[right] - changes[left+1] == 0
    upper = range_extreme(np.where(valid, close, np.nan), left, right, True)
    lower = range_extreme(np.where(valid, close, np.nan), left, right, False)
    result.loc[known, "path_status"] = "MISSING_OR_CONFLICTING_CLOSE_PATH"
    result.loc[complete, "path_status"] = "COMPLETE_CLOSE_PATH_INFERRED"
    result.loc[complete, "mfe"] = np.maximum.reduce([np.zeros(complete.sum()), upper[complete]/op[e[complete]]-1, result.loc[complete, "value"].to_numpy()])
    result.loc[complete, "mae"] = np.minimum.reduce([np.zeros(complete.sum()), lower[complete]/op[e[complete]]-1, result.loc[complete, "value"].to_numpy()])
    return result


def future_variance(features, days, origins):
    """Exactly 20 future daily log returns; do not bridge missing price sessions."""
    a = features.daily_log_return.to_numpy(float)
    oi = pd.DatetimeIndex(days).get_indexer(origins)
    end = oi + 20
    valid = end < len(days)
    end_clip = np.minimum(end, len(days)-1)
    sums = np.r_[0, np.cumsum(np.nan_to_num(a*a))]
    counts = np.r_[0, np.cumsum(np.isfinite(a))]
    valid &= counts[end_clip+1] - counts[oi+1] == 20
    value = (sums[end_clip+1] - sums[oi+1]) / 20
    value[~valid] = np.nan
    maturity = np.full(len(origins), np.datetime64("NaT"), dtype="datetime64[ns]")
    maturity[valid] = pd.DatetimeIndex(days).to_numpy()[end[valid]] + np.timedelta64(15, 'h')
    return value, maturity
