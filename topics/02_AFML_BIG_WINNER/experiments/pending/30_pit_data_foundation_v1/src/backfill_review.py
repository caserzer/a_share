"""Explicit source-page reviews: five original financial values and two merger timelines.

This small reviewed set is separate from bulk extraction candidates. It does not
certify whole financial statements, all revisions, cash settlement, or execution.
"""

import json
import re
import pandas as pd
from pypdf import PdfReader
from archive import CACHE, TOPIC, sha, write_json
from backfill_rpc import V2, PUBLIC
from pit import COLUMNS, Calendar, FactStore


def main():
    inv = pd.read_parquet(V2 / "inventory/securities.parquet").set_index("instrument")
    # Older sessions verify the pre-2017 notice; no weekday/calendar fabrication.
    old = pd.read_csv(
        TOPIC / "data/qlib/cn_data_pit_largecap/calendars/day.txt", header=None
    )[0]
    new = pd.read_parquet(V2 / "acquired/calendar.parquet")
    dates = sorted(
        set(pd.to_datetime(old).tolist())
        | set(
            pd.to_datetime(
                new.loc[new.is_trading_day.eq("1"), "calendar_date"]
            ).tolist()
        )
    )
    cal = Calendar(dates)
    facts, audit = [], []

    def add(
        instrument,
        field,
        value,
        effective,
        release,
        source,
        pages,
        recipe,
        index_sha=None,
    ):
        if sha(source["archive_path"]) != source["sha256"]:
            raise ValueError("review source changed")
        item = dict.fromkeys(COLUMNS)
        sid = inv.loc[instrument, "security_id"]
        item.update(
            record_id=instrument + "/" + field + "/original",
            logical_key=sid + "/" + field,
            security_id=sid,
            field=field,
            value=value,
            event_time=effective,
            effective_time=effective,
            known_at=cal.publication_time(release),
            source_observed_at=source["source_observed_at"],
            ingested_at=source.get("ingested_at", source["source_observed_at"]),
            source_uri=source["url"],
            source_path=source["archive_path"],
            source_sha256=source["sha256"],
            unit="CNY" if field.startswith("financial:") else "contract_scalar",
            original_version=source["url"].split("/")[-1],
            transform_sha256=sha(__file__),
            quality_tier="PIT-reconstructed",
            publication_evidence=json.dumps(
                dict(
                    release_date=release,
                    next_verified_session=True,
                    index_sha256=index_sha,
                    physical_pages=pages,
                ),
                ensure_ascii=False,
            ),
            reconstruction=recipe,
            supersedes=None,
        )
        facts.append(item)
        audit.append(
            dict(
                instrument=instrument,
                field=field,
                value=value,
                effective_date=effective,
                release_date=release,
                known_at=str(item["known_at"]),
                source_uri=source["url"],
                source_sha256=source["sha256"],
                physical_pages=json.dumps(pages),
                review="AGENT_SOURCE_PAGE_REVIEW_INDEPENDENT_HUMAN_REVIEW_FALSE",
                recipe=recipe,
            )
        )

    r = json.loads((V2 / "documents/financial/BJ920001_2025.json").read_text())
    source = dict(
        archive_path=r["source_path"],
        sha256=r["source_sha256"],
        url=r["source_uri"],
        source_observed_at=r["observed_at"],
    )
    text = PdfReader(r["source_path"]).pages[8].extract_text()
    expected = dict(
        revenue="212,838,536.28",
        net_profit_parent="-19,607,358.15",
        operating_cash_flow="6,998,800.24",
        total_assets="807,179,733.18",
        equity_parent="714,622,356.80",
    )
    if "2025" not in text or "单位：元" not in text:
        raise ValueError("reviewed financial table changed")
    h = r["index_source_sha256"]
    index = CACHE / "raw/sha256" / h[:2] / h
    if sha(index) != h:
        raise ValueError("original publication index changed")
    d = json.loads(index.read_text())
    if d["totalAnnouncement"] != len(d["announcements"]):
        raise ValueError("incomplete original report index")
    for field, literal in expected.items():
        if literal not in text:
            raise ValueError("reviewed first-column financial value missing")
        add(
            "BJ920001",
            f"financial:original_{field}:2025-12-31",
            float(literal.replace(",", "")),
            "2025-12-31",
            r["first_release_date"],
            source,
            [9],
            "Original 2025 annual report physical page 9; explicit CNY; first 2025 column; exact literal "
            + literal
            + "; original disclosure value only, later revision completeness unproven",
            h,
        )

    def event(art, instrument, release, specifications):
        source = json.loads((V2 / f"documents/events/{art}.json").read_text())
        evidence = []
        for p in (V2 / "documents/events").glob("index_*.json"):
            index = json.loads(p.read_text())
            for a in index["items"]:
                if a["art_code"] == art:
                    if a["notice_date"][:10] != release:
                        raise ValueError("event release index date disagreement")
                    evidence.append(index["sha256"])
        if not evidence:
            raise ValueError("missing archived event publication index")
        pdf = PdfReader(source["archive_path"])
        for field, value, effective, page, required, recipe in specifications:
            text = re.sub(r"\s+", "", pdf.pages[page - 1].extract_text() or "")
            if required not in text:
                raise ValueError("reviewed event clause absent: " + art + " " + field)
            add(
                instrument,
                field,
                value,
                effective,
                release,
                source,
                [page],
                recipe,
                evidence,
            )

    event(
        "AN201610300040928063",
        "SZ000748",
        "2016-10-31",
        [
            (
                "can_buy",
                False,
                "2016-11-01",
                2,
                "2016年11月1日起开始停牌",
                "Issuer explicitly states continuous suspension until conversion/termination; original old security cannot be bought",
            ),
            (
                "can_sell",
                False,
                "2016-11-01",
                2,
                "2016年11月1日起开始停牌",
                "Same original notice; no trading of old shares during continuous suspension",
            ),
            (
                "is_suspended",
                True,
                "2016-11-01",
                2,
                "不再交易",
                "Continuous suspension, not a fabricated missing quote",
            ),
        ],
    )
    event(
        "AN201701120262335661",
        "SZ000748",
        "2017-01-13",
        [
            (
                "listed",
                False,
                "2017-01-18",
                2,
                "终止上市日期：2017年1月18日",
                "Issuer original termination notice, listed=false from effective termination",
            ),
            (
                "merger:old_shares_per_new_share",
                0.5424,
                "2017-01-17",
                2,
                "每1股长城电脑新发行股份换取0.5424股长城信息股份",
                "Direction preserved: 0.5424 old SZ000748 shares per one new SZ000066 share; fractional-share allocation is not reconstructed",
            ),
            (
                "merger:successor_instrument",
                "SZ000066",
                "2017-01-17",
                2,
                "长城电脑",
                "Successor SZ000066 also explicitly identified on original pre-2017 suspension notice",
            ),
        ],
    )
    event(
        "AN201701120262561912",
        "SZ000748",
        "2017-01-13",
        [
            (
                "merger:new_shares_listing_date",
                "2017-01-18",
                "2017-01-18",
                19,
                "上市日为2017年1月18日",
                "New shares listing date; existing liens/lockups persist; no assumption of all-account free execution",
            ),
        ],
    )
    event(
        "AN201701230288265489",
        "SH600005",
        "2017-01-24",
        [
            (
                "can_buy",
                False,
                "2017-01-24",
                1,
                "2017年1月24日",
                "Original issuer notice: continuous suspension from Jan24; conservative known_at is next verified session",
            ),
            (
                "can_sell",
                False,
                "2017-01-24",
                1,
                "开市起连续停牌",
                "Continuous suspension until termination, old security cannot be sold",
            ),
        ],
    )
    event(
        "AN201702070325567429",
        "SH600005",
        "2017-02-08",
        [
            (
                "listed",
                False,
                "2017-02-14",
                1,
                "终止上市日期：2017年2月14日",
                "Issuer original termination date",
            ),
            (
                "merger:new_shares_per_old_share",
                0.56,
                "2017-02-14",
                1,
                "每1股本公司股票可换取0.56股宝钢股份股票",
                "One old SH600005 share converts to 0.56 new SH600019 shares; fractional-share allocation remains account dependent",
            ),
            (
                "merger:successor_instrument",
                "SH600019",
                "2017-02-14",
                1,
                "宝钢股份股票",
                "Successor instrument identified on implementation/listing original notice",
            ),
        ],
    )
    event(
        "AN201702210355506313",
        "SH600005",
        "2017-02-22",
        [
            (
                "merger:new_shares_listing_date",
                "2017-02-27",
                "2017-02-27",
                1,
                "上市流通日期为2017年2月27日",
                "Original completed share-swap result and new-share listing notice; not cash settlement or guaranteed fill",
            ),
        ],
    )
    exits = pd.read_parquet(V2 / "identity/bse_exits.parquet")
    for r in exits.itertuples():
        source = dict(
            archive_path=r.source_path,
            sha256=r.source_sha256,
            url=r.source_uri,
            source_observed_at=r.source_observed_at,
            ingested_at=r.ingested_at,
        )
        add(
            r.instrument,
            "listed",
            False,
            str(r.delist_date.date()),
            r.first_release_date,
            source,
            [r.physical_page],
            "Exact original issuer exit clause: " + r.exact_clause,
            r.index_source_sha256,
        )
    store = FactStore(facts)
    baseline = FactStore.from_parquet(CACHE / "vintages/facts.parquet")
    store.append(baseline.facts)
    store.to_parquet(V2 / "reviewed/facts.parquet")
    pd.DataFrame(audit).to_csv(PUBLIC / "reviewed_original_facts.csv", index=False)
    assert (
        store.get_asof(
            inv.loc["SZ000748", "security_id"], "can_buy", "2017-01-03 15:00"
        ).value
        is False
    )
    assert (
        store.get_asof(
            inv.loc["SH600005", "security_id"], "listed", "2017-02-13 15:00"
        ).value
        is None
    )
    field = "financial:original_revenue:2025-12-31"
    assert (
        store.get_asof(
            inv.loc["BJ920001", "security_id"], field, "2026-03-27 15:00"
        ).value
        is None
    )
    assert (
        store.get_asof(
            inv.loc["BJ920001", "security_id"], field, "2026-03-30 09:30"
        ).value
        == 212838536.28
    )
    write_json(
        PUBLIC / "reviewed_fact_summary.json",
        dict(
            records=len(facts),
            prior_v1_financial_vintage_records_retained=len(baseline.facts),
            financial_original_values=5,
            critical_merger_timelines=2,
            BSE_reviewed_exits=len(exits),
            independent_human_review=False,
            source_page_agent_review=True,
            full_statement_certified=False,
            all_corrections_certified=False,
            actual_execution_and_cash_settlement_known=False,
            first_financial_known_at=str(facts[0]["known_at"]),
            real_time_replay_assertions_passed=True,
        ),
    )


if __name__ == "__main__":
    main()
