"""Reconcile new official lists and public vendor history, preserving all assertions."""

import json
import uuid
from pathlib import Path
import pandas as pd
from archive import CACHE, write_json
from backfill_http import historical_attempts
from backfill_rpc import V2, PUBLIC


def stable_id(exchange, code, listing):
    return (
        "D2-"
        + uuid.uuid5(uuid.NAMESPACE_URL, f"cn-security/{exchange}/{code}/{listing}").hex
    )


def main():
    base = pd.read_parquet(CACHE / "identity/security_inventory.parquet")
    inventory = {r["instrument"]: r for r in base.to_dict("records")}
    assertions = []

    def add(
        instrument,
        exchange,
        name,
        listing,
        delist,
        board,
        provider,
        source_sha,
        orgid=None,
    ):
        listing = pd.to_datetime(listing, errors="coerce")
        delist = pd.to_datetime(delist, errors="coerce")
        assertions.append(
            dict(
                instrument=instrument,
                exchange=exchange,
                name=name,
                listing_date=listing,
                delist_date=delist,
                board_bucket=board,
                provider=provider,
                source_sha256=source_sha,
                org_id=orgid,
            )
        )
        if instrument not in inventory:
            sid = (
                stable_id(exchange, instrument[2:], str(listing.date()))
                if pd.notna(listing)
                else "D2-"
                + uuid.uuid5(
                    uuid.NAMESPACE_URL, "provisional-bse/" + str(orgid or instrument)
                ).hex
            )
            inventory[instrument] = dict(
                instrument=instrument,
                code=instrument[2:],
                exchange=exchange,
                name=name,
                listing_date=listing,
                delist_date=delist,
                board_bucket=board,
                is_delisted=pd.notna(delist),
                security_id=sid,
                metadata_source=provider,
                source_sha256=source_sha,
                org_id=orgid,
                identity_status="PROVISIONAL_NEVER_CERTIFIED_FROM_CURRENT_LIST",
                quality_tier="Historical-proxy",
            )
        elif provider.startswith("SZSE_"):
            r = inventory[instrument]
            # The new official assertion is explicit and old date assertions remain below.
            if pd.notna(listing):
                r["listing_date"] = listing
            if pd.notna(delist):
                r["delist_date"] = delist
                r["is_delisted"] = True
        if orgid:
            inventory[instrument]["org_id"] = orgid

    raw = historical_attempts()
    for r in base.to_dict("records"):
        assertions.append(
            dict(
                instrument=r["instrument"],
                exchange=r["exchange"],
                name=r["name"],
                listing_date=r["listing_date"],
                delist_date=r["delist_date"],
                board_bucket=r["board_bucket"],
                provider="D2_v1_frozen_assertion",
                source_sha256=r["source_sha256"],
            )
        )
    latest = {r["source_id"]: r for r in raw if r.get("http_status") == 200}
    for key, delisted in [("szse_xlsx_referer", False), ("szse_delisted_fixed", True)]:
        rec = latest[key]
        f = pd.read_excel(rec["archive_path"], dtype=str)
        for r in f.to_dict("records"):
            code = str(r.get("证券代码" if delisted else "A股代码", "")).zfill(6)
            if not code.startswith(("00", "30")) or not code.isdigit():
                continue
            add(
                "SZ" + code,
                "SZ",
                r.get("证券简称" if delisted else "A股简称"),
                r.get("上市日期" if delisted else "A股上市日期"),
                r.get("终止上市日期") if delisted else None,
                "chinext" if code.startswith("30") else "main_board",
                "SZSE_delisted" if delisted else "SZSE_current",
                rec["sha256"],
            )
    basic = V2 / "acquired/security_basic.parquet"
    if basic.exists():
        f = pd.read_parquet(basic)
        h = json.loads(Path(str(basic) + ".receipt.json").read_text())[
            "response_sha256"
        ][0]
        for r in f[f.type.eq("1")].to_dict("records"):
            market, code = r["code"].split(".")
            if market not in ["sh", "sz"] or not code.startswith(("6", "00", "30")):
                continue
            add(
                market.upper() + code,
                market.upper(),
                r["code_name"],
                r["ipoDate"],
                r["outDate"],
                "star"
                if code.startswith(("688", "689"))
                else "chinext"
                if code.startswith("30")
                else "main_board",
                "BaoStock_stock_basic",
                h,
            )
    rec = latest["cninfo_all_stock_registry"]
    cn = pd.DataFrame(json.loads(Path(rec["archive_path"]).read_bytes())["stockList"])
    cn = cn[cn.category.eq("A股")].copy()
    b = cn[cn.code.str.startswith(("92", "4", "8"))].copy()
    alias = []
    for org, g in b.groupby("orgId", sort=True):
        codes = sorted(g.code.tolist())
        primary = next((c for c in codes if c.startswith("92")), codes[0])
        r = g[g.code.eq(primary)].iloc[0]
        add(
            "BJ" + primary,
            "BJ",
            r.zwjc,
            None,
            None,
            "bse",
            "CNINFO_candidate_BSE_registry",
            rec["sha256"],
            org,
        )
        for code in codes:
            alias.append(
                dict(
                    org_id=org,
                    canonical_candidate="BJ" + primary,
                    alias="BJ" + code,
                    valid_from=None,
                    valid_to=None,
                    quality_tier="Historical-proxy",
                    reason="SHARED_CNINFO_ORG_ID_NOT_PROOF_OF_EFFECTIVE_CODE_MIGRATION",
                    source_sha256=rec["sha256"],
                )
            )
    for r in cn.itertuples():
        exchange = (
            "SH"
            if r.code.startswith("6")
            else "SZ"
            if r.code.startswith(("00", "30"))
            else None
        )
        if exchange and exchange + r.code in inventory:
            inventory[exchange + r.code]["org_id"] = r.orgId
    f = (
        pd.DataFrame(inventory.values())
        .sort_values("instrument")
        .reset_index(drop=True)
    )
    a = pd.DataFrame(assertions)
    conflicts = []
    for key, g in a.groupby("instrument"):
        for field in ["listing_date", "delist_date"]:
            values = sorted(set(str(x.date()) for x in g[field].dropna()))
            if len(values) > 1:
                conflicts.append(
                    dict(
                        instrument=key,
                        field=field,
                        values="|".join(values),
                        status="UNRESOLVED_IDENTITY_DATE_CONFLICT",
                        policy="ALL_ASSERTIONS_PRESERVED_STRICT_UNIVERSE_BLOCKED",
                    )
                )
    f["identity_date_conflict"] = f.instrument.isin(
        {r["instrument"] for r in conflicts}
    )
    target = V2 / "inventory"
    target.mkdir(parents=True, exist_ok=True)
    f.to_parquet(target / "securities.parquet", index=False)
    a.to_parquet(target / "assertions.parquet", index=False)
    pd.DataFrame(alias).to_parquet(target / "aliases.parquet", index=False)
    f.drop(columns=["source_path"], errors="ignore").to_csv(
        PUBLIC / "security_inventory.csv", index=False
    )
    pd.DataFrame(
        conflicts, columns=["instrument", "field", "values", "status", "policy"]
    ).to_csv(PUBLIC / "identity_conflicts.csv", index=False)
    pd.DataFrame(alias).to_csv(PUBLIC / "bse_alias_assertions.csv", index=False)
    write_json(
        PUBLIC / "inventory_summary.json",
        dict(
            v1_securities=len(base),
            v2_provisional_securities=len(f),
            added=len(f) - len(base),
            boards=f.board_bucket.value_counts().to_dict(),
            BSE_candidate_issuers=len(alias) and len(b.orgId.unique()),
            BSE_known_listing_dates=0,
            BSE_alias_rows=len(alias),
            date_conflicts=len(conflicts),
            complete_historical_population_certified=False,
        ),
    )
    print(
        "v2 inventory",
        len(f),
        "additional",
        len(f) - len(base),
        f.board_bucket.value_counts().to_dict(),
        flush=True,
    )


if __name__ == "__main__":
    main()
