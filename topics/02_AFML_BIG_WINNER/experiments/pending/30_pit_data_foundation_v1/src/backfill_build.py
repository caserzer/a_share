"""Build an independent D2 backfill release, retaining all conflicting observations.

This command changes only backfill_v2/normalized and its public audit products.
It never updates the baseline D2 or any EP01-29 data.
"""

import argparse
import json
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
from archive import CACHE, sha, write_json, utc_now
from backfill_rpc import V2, PUBLIC

PRICE_FIELDS = ["open", "high", "low", "close", "volume", "money", "turnover_rate"]
TOLERANCE = dict(
    open=0.0000001,
    high=0.0000001,
    low=0.0000001,
    close=0.0000001,
    volume=0.0,
    money=0.51,
    turnover_rate=0.000001,
)


def verified(path):
    receipt = Path(str(path) + ".receipt.json")
    r = json.loads(receipt.read_text())
    if sha(path) != r["parquet_sha256"]:
        raise ValueError("changed acquisition partition: " + str(path))
    hashes = r.get("response_sha256", [r.get("sha256")])
    for h in hashes:
        source = CACHE / "raw/sha256" / h[:2] / h
        if not source.exists() or sha(source) != h:
            raise ValueError("missing or changed original source: " + str(source))
    return pd.read_parquet(path), r


def reconcile_prices(frame):
    """Select one observed value only when all sources agree within declared precision.

    Amount differences up to CNY 0.51 accommodate integer-rounded Sina amounts.
    BaoStock is selected first for its explicit 4-decimal amount precision; all
    original values remain in observations. No averaging or return optimization.
    """
    frame = frame.copy()
    for c in PRICE_FIELDS:
        if c not in frame:
            frame[c] = np.nan
        frame[c] = pd.to_numeric(frame[c], errors="coerce")
        if c in ("open", "high", "low", "close"):
            frame.loc[frame[c].le(0), c] = np.nan
    frame["priority"] = frame.source_provider.map(
        {"BaoStock": 0, "Sina": 1, "D2-v1": 2}
    ).fillna(3)
    frame = frame.sort_values(["date", "priority"], kind="stable")
    g = frame.groupby("date", sort=True)
    result = g[PRICE_FIELDS].first()
    conflicts = []
    for field in PRICE_FIELDS:
        diff = g[field].max() - g[field].min()
        bad = diff.gt(TOLERANCE[field])
        for date in diff.index[bad]:
            rows = frame[frame.date.eq(date) & frame[field].notna()]
            conflicts.append(
                dict(
                    date=date,
                    field=field,
                    values=json.dumps(rows[field].tolist()),
                    providers=json.dumps(rows.source_provider.tolist()),
                    source_sha256s=json.dumps(rows.source_sha256.tolist()),
                )
            )
        result.loc[bad, field] = np.nan
        result[field + "_conflict"] = bad
    first = frame.drop_duplicates("date").set_index("date")
    result["source_sha256s"] = first.source_sha256.map(lambda x: [x])
    result["source_providers"] = first.source_provider.map(lambda x: [x])
    duplicate_dates = frame[frame.date.duplicated(keep=False)]
    if len(duplicate_dates):
        many = duplicate_dates.groupby("date")
        result.loc[many.size().index, "source_sha256s"] = many.source_sha256.agg(
            lambda x: sorted(set(x.dropna()))
        )
        result.loc[many.size().index, "source_providers"] = many.source_provider.agg(
            lambda x: sorted(set(x))
        )
    result["observation_count"] = g.size()
    # A status code is an archived vendor observation, never proof of an opening fill.
    for c in ["vendor_trade_status", "vendor_is_st"]:
        if c in frame:
            counts = g[c].nunique()
            result[c] = g[c].first().where(counts.le(1))
    result["can_buy"] = None
    result["can_sell"] = None
    result["quality_tier"] = "Historical-proxy"
    result["execution_reason"] = "FILL_AND_HISTORICAL_LIMIT_STATE_UNPROVEN"
    return result.reset_index(), conflicts


def bse_scope(inv):
    result = inv.copy()
    result["bse_listing_proxy"] = pd.NaT
    result["bse_listing_evidence"] = None
    path = V2 / "financials/bse_listing_assertions.parquet"
    if path.exists():
        f = pd.read_parquet(path)
        f = (
            f[~f.listing_date_conflict]
            .drop_duplicates("instrument")
            .set_index("instrument")
        )
        result["bse_listing_proxy"] = pd.to_datetime(
            result.instrument.map(f.listing_date)
        )
        result.loc[result.bse_listing_proxy.notna(), "bse_listing_evidence"] = (
            "LATER_ORIGINAL_ANNUAL_REPORT_ASSERTION"
        )
    ipo = pd.read_parquet(V2 / "acquired/bse_ipo.parquet")
    ipo["instrument"] = "BJ" + ipo.SECURITY_CODE
    dates = pd.to_datetime(
        result.instrument.map(ipo.set_index("instrument").SELECT_LISTING_DATE)
    )
    eligible = (
        result.exchange.eq("BJ")
        & result.bse_listing_proxy.isna()
        & dates.ge("2021-11-15")
    )
    result.loc[eligible, "bse_listing_proxy"] = dates[eligible]
    result.loc[eligible, "bse_listing_evidence"] = "RETROSPECTIVE_IPO_TABLE_ONLY"
    # The original 2021 rule explicitly transfers selected-tier companies to BSE.
    # The issuer/date table remains retrospective, so this stays a separate proxy.
    transition = V2 / "documents/bse_original_transition_rule.json"
    if transition.exists():
        r = json.loads(transition.read_text())
        if sha(r["archive_path"]) != r["sha256"]:
            raise ValueError("original BSE transition rule changed")
        eligible = (
            result.exchange.eq("BJ")
            & result.bse_listing_proxy.isna()
            & dates.lt("2021-11-15")
        )
        result.loc[eligible, "bse_listing_proxy"] = pd.Timestamp("2021-11-15")
        result.loc[eligible, "bse_listing_evidence"] = (
            "ORIGINAL_TRANSITION_RULE_PLUS_RETROSPECTIVE_SELECTED_TIER_DATE_PROXY"
        )
    for p in sorted((V2 / "documents/listings").glob("*.json")):
        r = json.loads(p.read_text())
        if r["status"] == "ORIGINAL_LISTING_NOTICE_MATCHED":
            match = result.instrument.eq(r["instrument"])
            result.loc[match, "bse_listing_proxy"] = pd.Timestamp(r["listing_date"])
            result.loc[match, "bse_listing_evidence"] = "ORIGINAL_ISSUER_LISTING_NOTICE"
    result["bse_first_quote_is_not_listing_date"] = True
    exits = V2 / "identity/bse_exits.parquet"
    if exits.exists():
        f = pd.read_parquet(exits).set_index("instrument")
        result["reviewed_BSE_exit_date"] = result.instrument.map(f.delist_date)
        result["delist_date"] = result.reviewed_BSE_exit_date.combine_first(
            result.delist_date
        )
        result.loc[result.reviewed_BSE_exit_date.notna(), "is_delisted"] = True
    return result


def source_tables(domain):
    frames = []
    for p in sorted((V2 / f"acquired/tables/{domain}").glob("*.parquet")):
        f, r = verified(p)
        f["source_sha256"] = r["sha256"]
        f["source_observed_at"] = r["source_observed_at"]
        f["source_uri"] = r["url"]
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


def normalize_tables(root, inv):
    mapping = inv.set_index("instrument").security_id
    shares = source_tables("shares")
    # BJ share records can still be tagged NQ in the historical vendor table.
    shares["instrument"] = shares.SECUCODE.str[-2:] + shares.SECURITY_CODE
    bse_aliases = pd.read_csv(PUBLIC / "bse_alias_assertions.csv", dtype=str)
    bj = {r.alias[2:]: r.canonical_candidate for r in bse_aliases.itertuples()}
    shares.loc[shares.SECURITY_CODE.isin(bj), "instrument"] = shares.SECURITY_CODE.map(
        bj
    )
    shares["security_id"] = shares.instrument.map(mapping)
    shares = shares[shares.security_id.notna()].copy()
    shares["effective_date"] = pd.to_datetime(shares.END_DATE)
    shares = shares.rename(
        columns={
            "TOTAL_SHARES": "total_shares",
            "LISTED_A_SHARES": "listed_a_shares",
            "FREE_SHARES": "free_shares",
        }
    )
    shares["known_at"] = pd.NaT
    shares["quality_tier"] = "Historical-proxy"
    shares["unit"] = "shares"
    shares["identity_mapping_status"] = np.where(
        shares.instrument.str.startswith("BJ"),
        "ORG_ALIAS_VALIDITY_INTERVAL_UNPROVEN",
        "EXCHANGE_CODE_PROXY",
    )
    share_conflicts = []
    coverage = []
    for row in inv.itertuples():
        new = shares[shares.security_id.eq(row.security_id)].copy()
        oldpath = CACHE / f"shares/{row.security_id}.parquet"
        old = pd.read_parquet(oldpath) if oldpath.exists() else pd.DataFrame()
        allrows = pd.concat([old, new], ignore_index=True)
        if allrows.empty:
            coverage.append(
                dict(
                    instrument=row.instrument,
                    security_id=row.security_id,
                    old_rows=0,
                    v2_rows=0,
                )
            )
            continue
        # Multiple source assertions remain separate. The reader blocks differing values.
        allrows = allrows.drop_duplicates(
            ["effective_date", "total_shares", "source_sha256"]
        )
        allrows["total_shares_conflict"] = (
            allrows.groupby("effective_date").total_shares.transform("nunique").gt(1)
        )
        allrows.sort_values("effective_date").to_parquet(
            root / f"shares/{row.security_id}.parquet", index=False
        )
        if allrows.total_shares_conflict.any():
            share_conflicts.extend(
                allrows[allrows.total_shares_conflict][
                    ["effective_date", "total_shares", "source_sha256"]
                ]
                .assign(instrument=row.instrument)
                .to_dict("records")
            )
        coverage.append(
            dict(
                instrument=row.instrument,
                security_id=row.security_id,
                old_rows=len(old),
                v2_rows=len(allrows),
                first_date=str(allrows.effective_date.min().date()),
            )
        )
    pd.DataFrame(coverage).to_csv(PUBLIC / "share_security_coverage.csv", index=False)
    pd.DataFrame(share_conflicts).to_csv(PUBLIC / "share_conflicts.csv", index=False)
    actions = source_tables("corporate_actions")
    actions["instrument"] = actions.SECUCODE.str[-2:] + actions.SECURITY_CODE
    actions["security_id"] = actions.instrument.map(mapping)
    actions = actions[actions.security_id.notna()].copy()
    cols = {
        "NOTICE_DATE": "notice_date",
        "PLAN_NOTICE_DATE": "plan_notice_date",
        "EQUITY_RECORD_DATE": "record_date",
        "EX_DIVIDEND_DATE": "ex_date",
        "REPORT_DATE": "report_period",
    }
    for a, b in cols.items():
        actions[b] = pd.to_datetime(actions[a])
    actions["cash_gross_CNY_per_share"] = (
        pd.to_numeric(actions.PRETAX_BONUS_RMB, errors="coerce") / 10
    )
    actions["bonus_shares_per_share"] = (
        pd.to_numeric(actions.BONUS_RATIO, errors="coerce") / 10
    )
    actions["capitalization_shares_per_share"] = (
        pd.to_numeric(actions.IT_RATIO, errors="coerce") / 10
    )
    actions["payment_date"] = pd.NaT
    actions["cash_settlement_status"] = "UNKNOWN_NO_ACTUAL_PAYMENT_DATE"
    actions["quality_tier"] = "Historical-proxy"
    actions["known_at"] = pd.NaT
    columns = [
        "instrument",
        "security_id",
        *cols.values(),
        "cash_gross_CNY_per_share",
        "bonus_shares_per_share",
        "capitalization_shares_per_share",
        "payment_date",
        "cash_settlement_status",
        "quality_tier",
        "known_at",
        "ASSIGN_PROGRESS",
        "IMPL_PLAN_PROFILE",
        "source_sha256",
        "source_observed_at",
        "source_uri",
    ]
    actions = actions[columns]
    actions.to_parquet(root / "corporate_actions.parquet", index=False)
    rights = source_tables("rights_issues")
    rights["instrument"] = rights.SECUCODE.str[-2:] + rights.SECURITY_CODE
    rights["security_id"] = rights.instrument.map(mapping)
    rights = rights[rights.security_id.notna()].copy()
    rights["subscription_shares_per_share"] = (
        pd.to_numeric(rights.PLACING_RATIO, errors="coerce") / 10
    )
    rights["subscription_price_CNY"] = pd.to_numeric(
        rights.ISSUE_PRICE, errors="coerce"
    )
    dates = {
        "FIRST_NOTICE_DATE": "notice_date",
        "EQUITY_RECORD_DATE": "record_date",
        "PAY_START_DATE": "pay_start_date",
        "PAY_END_DATE": "pay_end_date",
        "LISTING_DATE": "new_shares_listing_date",
        "EX_DIVIDEND_DATE": "ex_date",
    }
    for a, b in dates.items():
        rights[b] = pd.to_datetime(rights[a])
    rights["quality_tier"] = "Historical-proxy"
    rights["known_at"] = pd.NaT
    rights["actual_subscription_and_delivery"] = (
        "UNKNOWN_POLICY_AND_ORIGINAL_SETTLEMENT_EVIDENCE_REQUIRED"
    )
    columns = [
        "instrument",
        "security_id",
        *dates.values(),
        "subscription_shares_per_share",
        "subscription_price_CNY",
        "quality_tier",
        "known_at",
        "actual_subscription_and_delivery",
        "source_sha256",
        "source_observed_at",
        "source_uri",
    ]
    rights[columns].to_parquet(root / "rights_issues.parquet", index=False)
    return dict(
        share_securities=sum(x["v2_rows"] > 0 for x in coverage),
        share_source_conflict_rows=len(share_conflicts),
        corporate_action_rows=len(actions),
        rights_issue_rows=len(rights),
        payment_date_known=0,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-partial-market", action="store_true")
    args = parser.parse_args()
    if not args.allow_partial_market:
        state = json.loads((PUBLIC / "market_acquisition.json").read_text())
        if state["status"] != "ACQUIRED":
            raise ValueError("market acquisition incomplete")
    root = V2 / "normalized"
    for name in ["prices", "observations", "shares"]:
        (root / name).mkdir(parents=True, exist_ok=True)
    inv = bse_scope(pd.read_parquet(V2 / "inventory/securities.parquet"))
    inv.to_parquet(root / "securities.parquet", index=False)
    aliases = V2 / "identity/code_intervals.parquet"
    if aliases.exists():
        shutil.copyfile(aliases, root / "code_intervals.parquet")
    cal, _ = verified(V2 / "acquired/calendar.parquet")
    sessions = pd.to_datetime(cal.loc[cal.is_trading_day.eq("1"), "calendar_date"])
    pd.DataFrame({"date": sessions}).to_parquet(root / "calendar.parquet", index=False)
    reviewed = V2 / "reviewed/facts.parquet"
    if reviewed.exists():
        shutil.copyfile(reviewed, root / "reviewed_facts.parquet")
        shutil.copyfile(
            str(reviewed) + ".manifest.json",
            root / "reviewed_facts.parquet.manifest.json",
        )
    recent = []
    valuations = []
    for p in sorted((V2 / "acquired/daily").glob("*.parquet")):
        f, r = verified(p)
        if not f.adjustflag.eq("3").all():
            raise ValueError("adjusted price refused")
        f["instrument"] = f.code.str[:2].str.upper() + f.code.str[3:]
        f["date"] = pd.to_datetime(f.date)
        for c in PRICE_FIELDS:
            src = "amount" if c == "money" else "turn" if c == "turnover_rate" else c
            f[c] = pd.to_numeric(f[src], errors="coerce")
        f["turnover_rate"] /= 100
        f["source_sha256"] = r["response_sha256"][0]
        f["source_provider"] = "BaoStock"
        f["source_observed_at"] = r["observed_at"]
        v = f[
            [
                "date",
                "instrument",
                "peTTM",
                "pbMRQ",
                "psTTM",
                "pcfNcfTTM",
                "source_sha256",
                "source_observed_at",
            ]
        ].copy()
        v = v.rename(
            columns={
                "peTTM": "vendor_pe_ttm",
                "pbMRQ": "vendor_pb_mrq",
                "psTTM": "vendor_ps_ttm",
                "pcfNcfTTM": "vendor_pcf_ncf_ttm",
            }
        )
        for c in [
            "vendor_pe_ttm",
            "vendor_pb_mrq",
            "vendor_ps_ttm",
            "vendor_pcf_ncf_ttm",
        ]:
            v[c] = pd.to_numeric(v[c], errors="coerce")
        v["quality_tier"] = "Historical-proxy"
        v["known_at"] = pd.NaT
        valuations.append(v)
        f["vendor_trade_status"] = f.tradestatus
        f["vendor_is_st"] = f.isST
        recent.append(
            f[
                [
                    "date",
                    "instrument",
                    *PRICE_FIELDS,
                    "source_sha256",
                    "source_provider",
                    "source_observed_at",
                    "vendor_trade_status",
                    "vendor_is_st",
                ]
            ]
        )
    recent = pd.concat(recent, ignore_index=True)
    pd.concat(valuations, ignore_index=True).to_parquet(
        root / "vendor_valuations.parquet", index=False
    )
    unmapped = recent[~recent.instrument.isin(inv.instrument)]
    unmapped.to_parquet(root / "unmapped_daily_observations.parquet", index=False)
    grouped = {k: g for k, g in recent.groupby("instrument")}
    coverage, yearly, conflicts, quarantined = [], [], [], []
    for i, row in enumerate(inv.itertuples()):
        frames = []
        oldpath = CACHE / f"prices/{row.security_id}.parquet"
        old = pd.read_parquet(oldpath) if oldpath.exists() else pd.DataFrame()
        if len(old):
            old["source_provider"] = "D2-v1"
            frames.append(old)
        path = V2 / f"acquired/sina/{row.instrument}.parquet"
        if path.exists():
            f, r = verified(path)
            f["money"] = f["amount"] if "amount" in f else np.nan
            f["source_provider"] = "Sina"
            f["source_observed_at"] = r["source_observed_at"]
            frames.append(f)
        if row.instrument in grouped:
            frames.append(grouped[row.instrument])
        if not frames:
            coverage.append(
                dict(
                    instrument=row.instrument,
                    security_id=row.security_id,
                    board=row.board_bucket,
                    old_rows=0,
                    v2_rows=0,
                    status="NO_QUOTE_SOURCE",
                )
            )
            continue
        f = pd.concat(frames, ignore_index=True)
        f["date"] = pd.to_datetime(f.date)
        f["security_id"] = row.security_id
        f["quality_tier"] = "Historical-proxy"
        # Raw observations are retained even when their A-share membership is unresolved.
        f.to_parquet(root / f"observations/{row.security_id}.parquet", index=False)
        allowed = f.date.isin(sessions) & f.date.between("2017-01-03", "2026-10-21")
        if row.exchange == "BJ":
            allowed &= f.date.ge("2021-11-15")
            allowed &= (
                f.date.ge(row.bse_listing_proxy)
                if pd.notna(row.bse_listing_proxy)
                else False
            )
            if pd.notna(row.delist_date):
                allowed &= f.date.lt(row.delist_date)
        if (~allowed).any():
            quarantined.append(
                dict(
                    instrument=row.instrument,
                    observation_rows=int((~allowed).sum()),
                    reason="OUTSIDE_VERIFIED_CALENDAR_OR_BSE_LISTING_SCOPE",
                )
            )
        f = f[allowed]
        if f.empty:
            coverage.append(
                dict(
                    instrument=row.instrument,
                    security_id=row.security_id,
                    board=row.board_bucket,
                    old_rows=len(old),
                    v2_rows=0,
                    status="UNKNOWN_MARKET_SCOPE",
                )
            )
            continue
        merged, issues = reconcile_prices(f)
        merged["instrument"] = row.instrument
        merged["security_id"] = row.security_id
        merged["market_scope"] = (
            "BSE_LISTING_PROXY_NOT_STRICT_IDENTITY"
            if row.exchange == "BJ"
            else "A_SHARE_VENDOR_PROXY"
        )
        merged.to_parquet(root / f"prices/{row.security_id}.parquet", index=False)
        conflicts.extend(dict(instrument=row.instrument, **x) for x in issues)
        valid = merged.close.notna()
        coverage.append(
            dict(
                instrument=row.instrument,
                security_id=row.security_id,
                board=row.board_bucket,
                old_rows=len(old),
                v2_rows=len(merged),
                close_known_rows=int(valid.sum()),
                new_dates=int((~merged.date.isin(old.date if len(old) else [])).sum()),
                first_date=str(merged.date.min().date()),
                last_date=str(merged.date.max().date()),
                status="HISTORICAL_PROXY",
            )
        )
        for year, part in merged.groupby(merged.date.dt.year):
            yearly.append(
                dict(
                    instrument=row.instrument,
                    board=row.board_bucket,
                    year=year,
                    quote_dates=len(part),
                    close_known_rows=int(part.close.notna().sum()),
                    vendor_status_rows=int(
                        part.get("vendor_trade_status", pd.Series(dtype=str))
                        .notna()
                        .sum()
                    ),
                )
            )
        if i % 500 == 0:
            print("normalized", i, "/", len(inv), flush=True)
    pd.DataFrame(coverage).to_csv(PUBLIC / "quote_security_coverage.csv", index=False)
    pd.DataFrame(yearly).groupby(["board", "year"]).agg(
        securities=("instrument", "nunique"),
        quote_dates=("quote_dates", "sum"),
        close_known_rows=("close_known_rows", "sum"),
        vendor_status_rows=("vendor_status_rows", "sum"),
    ).reset_index().to_csv(PUBLIC / "board_year_coverage.csv", index=False)
    pd.DataFrame(
        conflicts,
        columns=[
            "instrument",
            "date",
            "field",
            "values",
            "providers",
            "source_sha256s",
        ],
    ).to_csv(PUBLIC / "price_conflicts.csv", index=False)
    pd.DataFrame(quarantined).to_csv(PUBLIC / "scope_quarantine.csv", index=False)
    result = normalize_tables(root, inv)
    write_json(
        PUBLIC / "normalization_summary.json",
        dict(
            **result,
            version="D2-v2-backfill-20261021",
            securities=len(inv),
            price_securities=sum(x["v2_rows"] > 0 for x in coverage),
            old_price_rows=sum(x["old_rows"] for x in coverage),
            v2_price_rows=sum(x["v2_rows"] for x in coverage),
            new_security_dates=sum(x.get("new_dates", 0) for x in coverage),
            price_conflict_fields=len(conflicts),
            unmapped_daily_observations=len(unmapped),
            BSE_listing_scope_known=int(inv.bse_listing_proxy.notna().sum()),
            built_at=utc_now(),
            root=str(root),
            strict_full_market_ready=False,
        ),
    )


if __name__ == "__main__":
    main()
