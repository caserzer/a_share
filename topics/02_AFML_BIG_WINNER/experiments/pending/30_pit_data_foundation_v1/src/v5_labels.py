"""All requested policies use user-authorized qfq price inference in v5.

Observed positive-volume opens are hypothetical execution points, never proof of
an actual fill, distributed cash, or realized retirement wealth.
"""
import json
import argparse
import time

import numpy as np
import pandas as pd

from archive import sha, write_json
from v5_core import EP, V5, PUBLIC, baseline, catalog, pin_sources

HORIZONS = ["6_calendar_months", "20_sessions", "60_sessions", "120_sessions"]
POLICIES = ["price", "total", "executable"]


def infer_labels(bars, days, origins, horizon, delist_date=pd.NaT):
    days, origins = pd.DatetimeIndex(days), pd.DatetimeIndex(origins)
    b = bars.sort_values("date").reset_index(drop=True)
    if b.date.duplicated().any():
        raise ValueError("ambiguous price dates")
    raw_open = pd.to_numeric(b.open, errors="coerce")
    positive = raw_open.gt(0) & np.isfinite(raw_open) & pd.to_numeric(b.volume, errors="coerce").gt(0)
    positive &= b.date.isin(days)
    if "vendor_trade_status" in b:
        positive &= ~pd.to_numeric(b.vendor_trade_status, errors="coerce").eq(0)
    # Conflicting opens remain an observed endpoint, but cannot yield a value.
    trades = b[positive].copy().reset_index(drop=True)
    trade_days = pd.DatetimeIndex(trades.date)
    trade_rows = list(trades.itertuples(index=False))
    trade_bar_indices = np.flatnonzero(positive.to_numpy())
    trade_calendar_indices = days.get_indexer(trade_days)
    all_dates = pd.DatetimeIndex(b.date)
    closes = pd.to_numeric(b.qfq_close, errors="coerce").to_numpy(dtype=float)
    close_valid = np.isfinite(closes) & (closes > 0) & all_dates.isin(days)
    if "close_conflict" in b:
        close_valid &= ~b.close_conflict.fillna(False).to_numpy(dtype=bool)
    chains = b.factor_chain_id.to_numpy()
    if horizon == "6_calendar_months":
        targets = days.searchsorted(origins + pd.DateOffset(months=6))
    else:
        targets = days.searchsorted(origins) + int(horizon.split("_")[0])
    origin_indices = days.searchsorted(origins)
    entry_indices = trade_days.searchsorted(origins, side="right")
    target_dates = pd.DatetimeIndex([days[j] if j < len(days) else days[-1] for j in targets])
    exit_candidates = trade_days.searchsorted(target_dates, side="left")
    rows = []
    for origin, origin_i, target_i, entry_i, exit_candidate in zip(origins, origin_indices, targets, entry_indices, exit_candidates):
        target = days[target_i] if target_i < len(days) else pd.NaT
        row = dict(date=origin, horizon=horizon, target_session=target,
            scheduled_entry_session=days[origin_i+1] if origin_i+1 < len(days) else pd.NaT,
            entry_date=pd.NaT, exit_date=pd.NaT, entry_qfq_open=np.nan, exit_qfq_open=np.nan,
            mature_at=pd.NaT,
            entry_raw_open=np.nan, exit_raw_open=np.nan, value=np.nan, raw_price_return=np.nan,
            qfq_minus_raw_return=np.nan, loss_below_minus20=None, mfe=np.nan, mae=np.nan,
            path_status="UNKNOWN", path_missing_sessions=None, entry_delay_sessions=None, exit_delay_sessions=None,
            status="UNKNOWN", reason="MISSING_OBSERVED_ENTRY_OPEN", terminal_rights_required=False,
            entry_factor_source_sha256=None, exit_factor_source_sha256=None,
            entry_factor_chain=None, exit_factor_chain=None)
        if pd.isna(target):
            row.update(status="CENSORED", reason="TARGET_BEYOND_VERIFIED_CALENDAR")
            rows.append(row)
            continue
        row["terminal_rights_required"] = pd.notna(delist_date) and target >= pd.Timestamp(delist_date)
        if row["terminal_rights_required"]:
            row["reason"] = "DELISTING_TERMINAL_VALUE_UNOBSERVED"
            rows.append(row)
            continue
        if entry_i >= len(trades):
            rows.append(row)
            continue
        entry = trade_rows[entry_i]
        row.update(entry_date=entry.date, entry_raw_open=float(entry.open),
                   entry_qfq_open=entry.qfq_open, entry_factor_source_sha256=entry.factor_source_sha256,
                   entry_factor_chain=entry.factor_chain_id,
                   entry_delay_sessions=int(trade_calendar_indices[entry_i] - origin_i - 1))
        if entry.date >= target:
            row["reason"] = "ENTRY_NOT_BEFORE_TARGET"
            rows.append(row)
            continue
        exit_i = max(exit_candidate, entry_i + 1)
        if exit_i >= len(trades):
            row["reason"] = "MISSING_OBSERVED_EXIT_OPEN"
            rows.append(row)
            continue
        exit_bar = trade_rows[exit_i]
        row.update(exit_date=exit_bar.date, exit_raw_open=float(exit_bar.open),
                   exit_qfq_open=exit_bar.qfq_open, exit_factor_source_sha256=exit_bar.factor_source_sha256,
                   exit_factor_chain=exit_bar.factor_chain_id,
                   exit_delay_sessions=int(trade_calendar_indices[exit_i] - target_i))
        if pd.notna(delist_date) and (entry.date >= pd.Timestamp(delist_date) or exit_bar.date >= pd.Timestamp(delist_date)):
            row.update(reason="DELISTING_TERMINAL_VALUE_UNOBSERVED", terminal_rights_required=True)
        elif bool(getattr(entry, "open_conflict", False)) or bool(getattr(exit_bar, "open_conflict", False)):
            row["reason"] = "UNRESOLVED_ENDPOINT_OPEN_CONFLICT"
        elif not np.isfinite(entry.qfq_open) or not np.isfinite(exit_bar.qfq_open) or entry.qfq_open <= 0 or exit_bar.qfq_open <= 0:
            row["reason"] = "MISSING_QFQ_ENDPOINT_FACTOR"
        elif entry.factor_chain_id != exit_bar.factor_chain_id:
            row["reason"] = "UNRECONCILED_CODE_CHANGE_FACTOR_SCALE"
        else:
            value = float(exit_bar.qfq_open / entry.qfq_open - 1)
            raw_value = float(exit_bar.open / entry.open - 1)
            row.update(status="KNOWN_INFERRED", reason="QFQ_OBSERVED_PRICE_CHANGE_EXECUTION_ASSUMED",
                       value=value, raw_price_return=raw_value, qfq_minus_raw_return=value-raw_value,
                       mature_at=exit_bar.date + pd.Timedelta(hours=9, minutes=30),
                       loss_below_minus20=bool(value < -0.2))
            first = trade_bar_indices[entry_i]
            last = trade_bar_indices[exit_i]
            complete = close_valid[first:last] & (chains[first:last] == entry.factor_chain_id)
            expected_count = trade_calendar_indices[exit_i] - trade_calendar_indices[entry_i]
            missing = int(expected_count - complete.sum())
            row["path_missing_sessions"] = missing
            if not missing:
                returns = np.r_[0.0, closes[first:last][complete]/entry.qfq_open - 1, value]
                row.update(path_status="COMPLETE_CLOSE_PATH_INFERRED", mfe=float(returns.max()), mae=float(returns.min()))
            else:
                row["path_status"] = "MISSING_OR_CONFLICTING_CLOSE_PATH"
        # Raw comparator is possible even if the adjustment factor is missing.
        if row["reason"] not in {"DELISTING_TERMINAL_VALUE_UNOBSERVED", "UNRESOLVED_ENDPOINT_OPEN_CONFLICT"}:
            row["raw_price_return"] = float(exit_bar.open / entry.open - 1)
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stream", action="store_true", help="consume atomic qfq partitions while factors are collected")
    args = parser.parse_args()
    versions = pin_sources()
    days = pd.DatetimeIndex(pd.read_parquet(baseline("inputs/baseline/normalized/calendar.parquet")).date)
    inv = pd.read_parquet(baseline("normalized/securities.parquet")).set_index("security_id")
    old = pd.read_parquet(baseline("normalized/full_monthly_bridge.parquet"))
    grid = old[old.v4_provisional_member].copy()
    assert not grid.duplicated(["date", "security_id"]).any()
    pieces = {h: [] for h in HORIZONS}
    groups = sorted(grid.groupby("security_id"), key=lambda x: inv.loc[x[0]].instrument)
    for i, (sid, group) in enumerate(groups):
        p = V5 / f"normalized/prices_qfq/{sid}.parquet"
        has_raw = any(x in catalog() for x in [f"normalized/prices/{sid}.parquet", f"inputs/baseline/normalized/prices/{sid}.parquet"])
        while args.stream and has_raw and not p.exists():
            if (V5 / "provider_gates/finance.sina.com.cn.stop").exists():
                raise PermissionError("factor provider stopped")
            time.sleep(0.5)
        if p.exists():
            bars = pd.read_parquet(p)
        else:
            bars = pd.DataFrame(columns=["date", "open", "volume", "qfq_open", "qfq_close", "factor_chain_id", "factor_source_sha256"])
            bars.date = pd.to_datetime(bars.date)
        for h in HORIZONS:
            f = infer_labels(bars, days, pd.DatetimeIndex(group.date), h, inv.loc[sid].delist_date)
            f["security_id"] = sid
            f["instrument"] = inv.loc[sid].instrument
            f["board_bucket"] = inv.loc[sid].board_bucket
            pieces[h].append(f)
        if i % 250 == 0:
            print("inferred labels", i, "/", grid.security_id.nunique(), flush=True)
    out = V5 / "normalized/labels"
    out.mkdir(parents=True, exist_ok=True)
    summary = []
    bridge = old.copy()
    for h, frames in pieces.items():
        f = pd.concat(frames, ignore_index=True)
        f["quality_tier"] = "Historical-proxy"
        f["adjustment_basis"] = "qfq"
        f["effective_policy"] = "qfq_price_change_inferred_for_all_requested_policies"
        f["execution_assumed"] = True
        f["strict_entry_execution_known"] = False
        f["strict_exit_execution_known"] = False
        f["actual_cash_and_terminal_wealth_verified"] = False
        f["label_method_version"] = "D2-v5-qfq-price-inference"
        for policy in POLICIES:
            f["return_policy"] = policy
            f.to_parquet(out / f"{h}_{policy}.parquet", index=False)
            for (board, status, reason), g in f.groupby(["board_bucket", "status", "reason"], dropna=False):
                summary.append(dict(horizon=h, requested_policy=policy, board_bucket=board, status=status, reason=reason,
                                    rows=len(g), complete_path_rows=int(g.mfe.notna().sum())))
        short = h.replace("_calendar_months", "m").replace("_sessions", "d")
        columns = ["date", "security_id", "value", "raw_price_return", "status", "reason", "entry_date", "exit_date", "loss_below_minus20", "mfe", "mae"]
        add = f[columns].rename(columns={"security_id": "v4_canonical_security_id", **{k:"v5_qfq_"+short+"_"+k for k in columns if k not in {"date", "security_id"}}})
        bridge = bridge.merge(add, on=["date", "v4_canonical_security_id"], how="left", validate="many_to_one", sort=False)
    # Every old row and column is unchanged, including retained legacy aliases.
    pd.testing.assert_frame_equal(old.reset_index(drop=True), bridge[old.columns].reset_index(drop=True))
    bridge.to_parquet(V5 / "normalized/full_monthly_bridge.parquet", index=False)
    pd.DataFrame(summary).to_csv(PUBLIC / "label_coverage.csv", index=False)
    totals = pd.DataFrame(summary).groupby(["horizon", "requested_policy", "status"]).rows.sum().reset_index()
    totals.to_csv(PUBLIC / "label_status_totals.csv", index=False)
    six = bridge[bridge.v4_provisional_member]
    known = six.v5_qfq_6m_status.eq("KNOWN_INFERRED")
    comparison = dict(candidate_months=len(grid), bridge_rows=len(bridge), old_bridge_columns_preserved=len(old.columns),
        label_rows=sum(x["rows"] for x in summary), known_inferred_rows=sum(x["rows"] for x in summary if x["status"]=="KNOWN_INFERRED"),
        six_month_known=int(known.sum()), six_month_qfq_loss_below_minus20=int(six.loc[known,"v5_qfq_6m_value"].lt(-0.2).sum()),
        six_month_raw_loss_below_minus20=int(six.loc[known,"v5_qfq_6m_raw_price_return"].lt(-0.2).sum()),
        six_month_loss_classification_changed=int((six.loc[known,"v5_qfq_6m_value"].lt(-0.2) != six.loc[known,"v5_qfq_6m_raw_price_return"].lt(-0.2)).sum()),
        policy_aliases_are_same_price_inference=True, raw_to_qfq_comparison_uses_same_entry_exit=True,
        no_actual_execution_or_wealth_certification=True, transform_source_hashes=versions)
    write_json(PUBLIC / "label_summary.json", comparison)


if __name__ == "__main__":
    main()
