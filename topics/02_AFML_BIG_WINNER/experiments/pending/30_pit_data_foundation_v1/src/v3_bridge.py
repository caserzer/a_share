"""Full monthly bridge and fail-closed labels under the unchanged D2 contract.

The bulk fast path is valid only when every source execution flag is unknown.
It proves the entry blocker, rather than turning observed trading into an open fill.
Raw scheduled-open comparisons are separate diagnostics, never strict labels.
"""

import numpy as np
import pandas as pd
from archive import sha, write_json
from v3_core import V3, PUBLIC3, V2_RELEASE, inventory, code_version

HORIZONS = ["6_calendar_months", "20_sessions", "60_sessions", "120_sessions"]
POLICIES = ["price", "total", "executable"]


def target_indices(days, origins, horizon):
    if horizon == "6_calendar_months":
        wanted = origins + pd.DateOffset(months=6)
        return days.searchsorted(wanted)
    return days.searchsorted(origins) + int(horizon.split("_")[0])


def entry_blockers(days, origins, bars):
    """An explicit positive/negative flag needs the full sequential label engine."""
    for field in ["can_buy", "can_sell"]:
        if field in bars and bars[field].notna().any():
            raise ValueError(
                "bulk unknown-entry fast path cannot process explicit execution flags"
            )
    following = days.searchsorted(origins, side="right")
    result = np.full(len(origins), "MISSING_EXECUTION_STATUS_OR_SOURCE", dtype=object)
    usable = following < len(days)
    if usable.any():
        result[usable] = np.where(
            days[following[usable]].isin(pd.DatetimeIndex(bars.date)),
            "UNKNOWN_BUY_EXECUTION",
            "MISSING_EXECUTION_STATUS_OR_SOURCE",
        )
    return result


def candidate_months(inv, days):
    month_ends = pd.Series(days).groupby(days.to_period("M")).max()
    # The current partial calendar month is never called a completed origin month.
    month_ends = pd.DatetimeIndex(
        month_ends[month_ends.dt.to_period("M") < days[-1].to_period("M")]
    )
    rows = []
    for r in inv.itertuples():
        start = r.listing_date
        if pd.isna(start) and r.exchange == "BJ":
            start = r.bse_listing_proxy
        if pd.isna(start):
            continue
        keep = month_ends >= pd.Timestamp(start)
        if not pd.isna(r.delist_date):
            keep &= month_ends < pd.Timestamp(r.delist_date)
        origins = month_ends[keep]
        if not len(origins):
            continue
        rows.append(
            pd.DataFrame(
                dict(
                    date=origins,
                    security_id=r.security_id,
                    instrument=r.instrument,
                    board_bucket=r.board_bucket,
                    exchange=r.exchange,
                    provisional_population=True,
                    population_boundary_quality="Historical-proxy",
                    identity_date_conflict=bool(r.identity_date_conflict),
                    original_listing_qualification_proven=False,
                    full_daily_status_coverage=False,
                )
            )
        )
    return pd.concat(rows, ignore_index=True)


def main():
    PUBLIC3.mkdir(parents=True, exist_ok=True)
    normalized = V3 / "normalized"
    normalized.mkdir(parents=True, exist_ok=True)
    version = code_version(__file__)
    days = pd.DatetimeIndex(
        pd.read_parquet(V2_RELEASE / "normalized/calendar.parquet").date
    )
    updated = V3 / "normalized/securities.parquet"
    inv = pd.read_parquet(updated) if updated.exists() else inventory()
    grid = candidate_months(inv, days)
    states = pd.read_parquet(V3 / "normalized/status_facts.parquet")
    grid["original_status_evidence_rows_asof_origin"] = 0
    for sid, indices in grid.groupby("security_id").groups.items():
        f = states[states.security_id.eq(sid)]
        if f.empty:
            continue
        visible = pd.concat(
            [f.known_at.dt.tz_localize(None), f.effective_time.dt.tz_localize(None)],
            axis=1,
        ).max(axis=1)
        instants = np.sort(visible.to_numpy(dtype="datetime64[ns]"))
        decisions = (
            pd.to_datetime(grid.loc[indices, "date"]) + pd.Timedelta(hours=15)
        ).to_numpy()
        grid.loc[indices, "original_status_evidence_rows_asof_origin"] = (
            np.searchsorted(instants, decisions, side="right")
        )
    excluded = inv[~inv.security_id.isin(grid.security_id)].copy()
    excluded["no_completed_month_reason"] = (
        "NO_COMPLETED_MONTH_IN_LISTING_INTERVAL_OR_UNPROVEN_START"
    )
    excluded.loc[excluded.delist_date.lt("2017-01-03"), "no_completed_month_reason"] = (
        "DELISTED_BEFORE_REQUESTED_WINDOW"
    )
    starts = excluded.listing_date.combine_first(
        pd.to_datetime(excluded.bse_listing_proxy)
    )
    excluded.loc[starts.gt(grid.date.max()), "no_completed_month_reason"] = (
        "FIRST_COMPLETED_LISTING_MONTH_AFTER_ORIGIN_CUTOFF"
    )
    excluded.loc[starts.isna(), "no_completed_month_reason"] = (
        "LISTING_START_NOT_PROVEN_OR_AVAILABLE"
    )
    excluded[
        [
            "security_id",
            "instrument",
            "listing_date",
            "bse_listing_proxy",
            "delist_date",
            "no_completed_month_reason",
        ]
    ].to_csv(PUBLIC3 / "population_without_candidate_months.csv", index=False)
    legacy_path = (
        V2_RELEASE / "normalized/legacy_bridge_with_v2_quote_availability.parquet"
    )
    old = pd.read_parquet(legacy_path)
    keys = ["date", "security_id"]
    old["date"] = pd.to_datetime(old.date)
    if old.duplicated(keys).any() or grid.duplicated(keys).any():
        raise ValueError("bridge key conflict; never silently collapse identities")
    # Keep all old columns byte-for-value, including historical code aliases.
    bridge = old.merge(
        grid.rename(columns={"instrument": "v3_instrument", "exchange": "v3_exchange"}),
        on=keys,
        how="outer",
        validate="one_to_one",
        indicator="v3_bridge_membership",
    )
    bridge["v3_provisional_member"] = bridge.provisional_population.fillna(
        False
    ).astype(bool)
    for column in old.columns:
        original = old.set_index(keys)[column] if column not in keys else None
        if original is not None:
            actual = bridge.set_index(keys).loc[original.index, column]
            pd.testing.assert_series_equal(
                original, actual, check_dtype=False, check_names=False
            )
    bridge_path = normalized / "full_monthly_bridge.parquet"
    bridge.to_parquet(bridge_path, index=False)
    by_sid = {
        sid: frame.sort_values("date")
        for sid, frame in grid.groupby("security_id", sort=True)
    }
    meta = inv.set_index("security_id")
    pieces = {h: [] for h in HORIZONS}
    for i, (sid, group) in enumerate(by_sid.items()):
        path = V3 / f"normalized/prices/{sid}.parquet"
        if not path.exists():
            path = V2_RELEASE / f"normalized/prices/{sid}.parquet"
        bars = (
            pd.read_parquet(path)
            if path.exists()
            else pd.DataFrame(columns=["date", "open", "close"])
        )
        bars["date"] = pd.to_datetime(bars.date)
        bars = bars.sort_values("date")
        origins = pd.DatetimeIndex(group.date)
        reasons = entry_blockers(days, origins, bars)
        scheduled_entry_i = days.searchsorted(origins, side="right")
        entry_dates = pd.DatetimeIndex(
            [days[j] if j < len(days) else pd.NaT for j in scheduled_entry_i]
        )
        indexed = bars.set_index("date")
        opens = pd.to_numeric(indexed.open, errors="coerce")
        entry_open = opens.reindex(entry_dates).to_numpy(dtype=float)
        out = meta.loc[sid].delist_date
        for horizon in HORIZONS:
            targets = target_indices(days, origins, horizon)
            mature = targets < len(days)
            target_dates = pd.DatetimeIndex(
                [days[j] if j < len(days) else pd.NaT for j in targets]
            )
            target_open = opens.reindex(target_dates).to_numpy(dtype=float)
            f = group[
                [
                    "date",
                    "security_id",
                    "instrument",
                    "board_bucket",
                    "identity_date_conflict",
                    "original_status_evidence_rows_asof_origin",
                ]
            ].copy()
            f["horizon"] = horizon
            f["scheduled_entry_session_diagnostic"] = entry_dates
            f["target_session"] = target_dates
            f["status"] = np.where(mature, "UNKNOWN", "CENSORED")
            f["reason"] = np.where(mature, reasons, "TARGET_BEYOND_VERIFIED_CALENDAR")
            f["strict_entry_execution_known"] = False
            f["strict_exit_execution_known"] = False
            f["independent_complete_action_ledger"] = False
            f["actual_settlement_coverage"] = False
            f["terminal_rights_required"] = (
                False if pd.isna(out) else target_dates >= pd.Timestamp(out)
            )
            f["terminal_value_known"] = False
            valid = mature & (entry_open > 0) & (target_open > 0)
            if not pd.isna(out):
                valid &= (entry_dates < pd.Timestamp(out)) & (
                    target_dates < pd.Timestamp(out)
                )
            if "vendor_trade_status" in indexed:
                traded = pd.to_numeric(indexed.vendor_trade_status, errors="coerce")
                valid &= ~traded.reindex(entry_dates).eq(0).to_numpy()
                valid &= ~traded.reindex(target_dates).eq(0).to_numpy()
            f["scheduled_open_price_proxy"] = np.where(
                valid, target_open / entry_open - 1, np.nan
            )
            f["scheduled_open_price_proxy_quality"] = (
                "Historical-proxy_NOT_EXECUTION_OR_TOTAL_RETURN"
            )
            f["value"] = np.nan
            f["loss_below_minus20"] = pd.Series(
                [None] * len(f), index=f.index, dtype=object
            )
            f["mfe"] = np.nan
            f["mae"] = np.nan
            f["quality_tier"] = "UNKNOWN/BLOCKED"
            pieces[horizon].append(f)
        if i % 500 == 0:
            print("monthly bridge", i + 1, "/", len(by_sid), flush=True)
    summaries, groups, artifacts = [], [], []
    for horizon, frames in pieces.items():
        base = pd.concat(frames, ignore_index=True)
        for policy in POLICIES:
            f = base.copy()
            f["return_policy"] = policy
            f["requires_complete_action_ledger"] = policy != "price"
            f["requires_actual_cash_and_costs"] = policy == "executable"
            f["execution_cost_bps"] = np.nan
            p = normalized / f"labels/{horizon}/{policy}.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            f.to_parquet(p, index=False)
            artifacts.append(
                dict(path=str(p.relative_to(V3)), sha256=sha(p), rows=len(f))
            )
            summary = (
                f.groupby(
                    ["horizon", "return_policy", "status", "reason"], dropna=False
                )
                .size()
                .reset_index(name="rows")
            )
            summaries.append(summary)
            f["year"] = f.date.dt.year
            groups.append(
                f.groupby(
                    ["board_bucket", "year", "horizon", "return_policy", "status"],
                    dropna=False,
                )
                .size()
                .reset_index(name="rows")
            )
    pd.concat(summaries, ignore_index=True).to_csv(
        PUBLIC3 / "strict_label_counts.csv", index=False
    )
    pd.concat(groups, ignore_index=True).to_csv(
        PUBLIC3 / "strict_labels_by_board_year.csv", index=False
    )
    grid.groupby(["board_bucket", grid.date.dt.year]).size().reset_index(
        name="rows"
    ).to_csv(PUBLIC3 / "full_bridge_population_by_board_year.csv", index=False)
    write_json(
        PUBLIC3 / "full_bridge_summary.json",
        dict(
            securities_with_candidate_months=grid.security_id.nunique(),
            candidate_month_rows=len(grid),
            first_origin=str(grid.date.min().date()),
            last_origin=str(grid.date.max().date()),
            legacy_rows_preserved=len(old),
            legacy_columns_preserved=list(old.columns),
            legacy_sha256=sha(legacy_path),
            union_bridge_rows=len(bridge),
            new_month_or_identity_rows=int(
                bridge.v3_bridge_membership.eq("right_only").sum()
            ),
            bridge_sha256=sha(bridge_path),
            labels=artifacts,
            transform_sha256=version,
            bulk_fast_path_precondition="all source can_buy/can_sell flags are null; enforced per security",
            strict_known=0,
            proxy_diagnostics_are_not_strict_labels=True,
            inventory_sha256=sha(updated) if updated.exists() else None,
            status_facts_sha256=sha(V3 / "normalized/status_facts.parquet"),
            population_not_certified_from_current_metadata=True,
        ),
    )


if __name__ == "__main__":
    main()
