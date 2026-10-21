"""Explicit original-page review of a three-vintage 2020 report chain.

Agent review is not independent human acceptance. Other extracted values stay
unreviewed. The original positive cash flow must survive before the 2023 revision.
"""

import json
from decimal import Decimal
import pandas as pd
from archive import sha, write_json
from pit import COLUMNS, FactStore
from v3_core import V3, PUBLIC3, inventory, code_version
from v3_evidence import (
    original_pages,
    printed_security,
    security_map,
    calendar,
    compact,
)

CASES = [
    (
        "AN202104201486637512",
        "2021-04-20",
        {
            "revenue": "291,969,753.96",
            "net_profit_parent": "17,284,751.61",
            "operating_cash_flow": "4,456,443.98",
            "total_assets": "266,673,467.32",
            "equity_parent": "44,178,502.53",
        },
    ),
    (
        "AN202106231499541174",
        "2021-06-23",
        {
            "revenue": "291,969,753.96",
            "net_profit_parent": "17,284,751.61",
            "operating_cash_flow": "4,456,443.98",
            "total_assets": "266,673,467.32",
            "equity_parent": "44,178,502.53",
        },
    ),
    (
        "AN202304041585128585",
        "2023-04-04",
        {
            "revenue": "286,891,192.04",
            "net_profit_parent": "18,514,918.94",
            "operating_cash_flow": "-4,549,865.76",
            "total_assets": "265,760,467.01",
            "equity_parent": "40,175,064.33",
        },
    ),
]


def build():
    inv, cal, mapping = inventory(), calendar(), security_map()
    sid = inv.loc[inv.instrument.eq("BJ920132"), "security_id"].iloc[0]
    facts, audit, predecessors = [], [], {}
    version = code_version(__file__)
    for art, published, values in CASES:
        r = json.loads((V3 / f"documents/financial/{art}.json").read_text())
        a, source = r["announcement"], r["source"]
        if (
            a["security_id"] != sid
            or a["report_period"] != "2020-12-31"
            or a["notice_date"] != published
        ):
            raise ValueError("reviewed version identity/period/publication mismatch")
        pages = original_pages(source["archive_path"], source["sha256"])
        if printed_security(pages, mapping) != sid or "单位:元" not in compact(
            pages[8]
        ):
            raise ValueError("reviewed issuer or CNY table unit changed")
        if "本期上年同期" not in compact(pages[8]) or "本期期末上年期末" not in compact(
            pages[8]
        ):
            raise ValueError("reviewed current/comparative column headers changed")
        for name, literal in values.items():
            if literal not in pages[8]:
                raise ValueError("reviewed physical page 9 literal changed")
            corroborating_pages = [
                i + 1 for i, t in enumerate(pages) if i >= 30 and literal in t
            ]
            if not corroborating_pages:
                raise ValueError("reviewed financial-statement corroboration missing")
            field = "financial:reviewed_reported_" + name + ":2020-12-31"
            rid = art + "/" + field
            f = dict.fromkeys(COLUMNS)
            f.update(
                record_id=rid,
                logical_key=sid + "/" + field,
                security_id=sid,
                field=field,
                value=float(Decimal(literal.replace(",", ""))),
                event_time="2020-12-31",
                effective_time="2020-12-31",
                known_at=cal.publication_time(published),
                source_observed_at=source["source_observed_at"],
                ingested_at=source["ingested_at"],
                source_uri=source["url"],
                source_path=source["archive_path"],
                source_sha256=source["sha256"],
                unit="CNY",
                original_version=art,
                transform_sha256=version,
                quality_tier="PIT-reconstructed",
                publication_evidence=json.dumps(
                    dict(
                        index_sha256=a["index_sha256"],
                        published=published,
                        date_only_next_verified_open=True,
                    )
                ),
                reconstruction=f"Agent source-page review: original 2020 cover; physical page 9; explicit CNY; current-period first column; exact {literal}; corroborating statement pages {corroborating_pages}; independent human review=false",
                supersedes=predecessors.get(field),
            )
            facts.append(f)
            audit.append(
                dict(
                    art_code=art,
                    security_id=sid,
                    field=field,
                    source_literal=literal,
                    physical_page=9,
                    statement_pages=json.dumps(corroborating_pages),
                    known_at=str(f["known_at"]),
                    source_sha256=source["sha256"],
                    index_sha256=a["index_sha256"],
                    supersedes=f["supersedes"],
                    independent_human_review=False,
                )
            )
            predecessors[field] = rid
    store = FactStore(facts)
    target = V3 / "normalized/financial_reviewed_facts.parquet"
    store.to_parquet(target)
    pd.DataFrame(audit).to_csv(
        PUBLIC3 / "financial_source_page_reviews.csv", index=False
    )
    field = "financial:reviewed_reported_operating_cash_flow:2020-12-31"
    replay = []
    for date, expected in [
        ("2021-04-20 15:00", None),
        ("2021-04-21 09:30", 4456443.98),
        ("2021-06-24 09:30", 4456443.98),
        ("2023-04-04 15:00", 4456443.98),
        ("2023-04-06 09:30", -4549865.76),
    ]:
        result = store.get_asof(sid, field, date)
        if result.value != expected:
            raise ValueError(
                "financial revision leaked or was unavailable at verified boundary"
            )
        assert store.get_asof(sid, field, date, mode="archived").value is None
        replay.append(
            dict(
                decision_time=date,
                field=field,
                historical_value=result.value,
                original_versions=[r["original_version"] for r in result.records],
                archived_value=None,
            )
        )
    early = FactStore([f for f in facts if pd.Timestamp(f["known_at"]).year < 2023])
    assert (
        early.get_asof(sid, field, "2022-12-30 15:00").value
        == store.get_asof(sid, field, "2022-12-30 15:00").value
    )
    write_json(
        PUBLIC3 / "financial_revision_replay.json",
        dict(
            status="PASS",
            source_versions=3,
            reviewed_fields=5,
            facts=len(facts),
            replay=replay,
            future_version_deletion_invariant=True,
            archive_not_backdated=True,
            reviewed_version_namespace_does_not_claim_all_amendments_field_complete=True,
            independent_human_review=False,
            reviewed_facts_sha256=sha(target),
            transform_sha256=version,
        ),
    )


if __name__ == "__main__":
    build()
