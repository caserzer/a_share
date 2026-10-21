"""Explicit agent-reviewed source pages; never attest an account settlement."""

import json
import re
from decimal import Decimal
from pathlib import Path

import pandas as pd

from archive import archive_bytes, sha, write_json
from pit import COLUMNS, FactStore, stamp
from v4_core import PUBLIC, V4, baseline, source_bytes, original_document
from v4_pipeline import calendar, original_pages

VERSION = archive_bytes(Path(__file__).read_bytes(), root=V4)[1]
FINANCIAL = [
    (
        "AN202011231432078352",
        "SZ002680",
        "2018-12-31",
        "2020-11-23",
        {
            "revenue": (9, "7,365,122.28"),
            "net_profit_parent": (9, "-3,243,183,798.05"),
            "operating_cash_flow": (9, "-203,122,781.04"),
            "total_assets": (9, "325,727,935.52"),
            "equity_parent": (9, "240,602,221.70"),
        },
    ),
    (
        "AN202104301488798383",
        "SH600687",
        "2020-12-31",
        "2021-04-30",
        {
            "revenue": (8, "354,644,432.38"),
            "net_profit_parent": (8, "-2,248,069,361.08"),
            "operating_cash_flow": (9, "-12,946,895.75"),
            "total_assets": (9, "5,991,766,578.54"),
            "equity_parent": (9, "-752,945,094.88"),
        },
    ),
    (
        "AN202105261494081138",
        "SH600687",
        "2020-12-31",
        "2021-05-26",
        {
            "revenue": (8, "354,644,432.38"),
            "net_profit_parent": (8, "-2,248,069,361.08"),
            "operating_cash_flow": (9, "-12,946,895.75"),
            "total_assets": (9, "5,991,766,578.54"),
            "equity_parent": (9, "-752,945,094.88"),
        },
    ),
]
REMOVALS = [
    (
        "AN202401221617905970",
        "SH600290",
        "2024-01-16",
        "华仪电气股份有限公司已于2024年1月16日在上海证券交易所摘牌并终止上市",
    ),
    (
        "AN202402011620009103",
        "SZ002776",
        "2024-01-25",
        "广东柏堡龙股份有限公司已于2024年1月25日在深圳证券交易所摘牌并终止上市",
    ),
]


def fact(
    sid, field, value, effective, known, art, source, index_sha, unit, reconstruction
):
    row = dict.fromkeys(COLUMNS)
    row.update(
        record_id=art + "/" + field,
        logical_key=sid + "/" + field,
        security_id=sid,
        field=field,
        value=value,
        event_time=effective,
        effective_time=effective,
        known_at=known,
        source_observed_at=source["source_observed_at"],
        ingested_at=source["ingested_at"],
        source_uri=source["url"],
        source_path=str(source_bytes(source)),
        source_sha256=source["sha256"],
        unit=unit,
        original_version=art,
        transform_sha256=VERSION,
        quality_tier="PIT-reconstructed",
        publication_evidence=json.dumps(
            dict(index_sha256=index_sha, date_only_next_verified_session=True)
        ),
        reconstruction=reconstruction
        + "; agent original-pixel review; independent human review=false",
    )
    return row


def build():
    inv = pd.read_parquet(baseline("normalized/securities.parquet")).set_index(
        "instrument"
    )
    cal = calendar()
    for reviewed in json.loads(
        (
            Path(__file__).resolve().parents[1] / "configs/v4_source_page_reviews.json"
        ).read_text()
    ):
        for image in reviewed["images"]:
            if sha(V4 / image["path"]) != image["sha256"]:
                raise ValueError("changed pinned reviewed page image")
        if reviewed["art_code"].startswith("AN2020") or reviewed["art_code"] in {
            x[0] for x in FINANCIAL
        }:
            record = json.loads(
                (V4 / f"documents/financial/{reviewed['art_code']}.json").read_text()
            )
        else:
            record = original_document(reviewed["art_code"], reviewed["source_sha256"])
        if record["source"]["sha256"] != reviewed["source_sha256"]:
            raise ValueError("changed pinned reviewed original source")
    facts, audit, predecessor = [], [], {}
    for art, instrument, period, date, values in FINANCIAL:
        doc = json.loads((V4 / f"documents/financial/{art}.json").read_text())
        a, source = doc["announcement"], doc["source"]
        sid = inv.loc[instrument].security_id
        if (a["security_id"], a["report_period"], a["notice_date"]) != (
            sid,
            period,
            date,
        ):
            raise ValueError("reviewed financial source identity/period/date changed")
        pages = original_pages(source)
        known = stamp(a["known_at"])
        for field, (page, literal) in values.items():
            text = re.sub(r"\s+", "", pages[page - 1])
            if literal not in text:
                raise ValueError("reviewed table literal changed")
            image = V4 / f"reviews/financial/{art}_page{page}.png"
            if not image.exists():
                raise ValueError("reviewed financial page image missing")
            name = "financial:reviewed_reported_" + field + ":" + period
            f = fact(
                sid,
                name,
                float(Decimal(literal.replace(",", ""))),
                period,
                known,
                art,
                source,
                a["index_sha256"],
                "CNY",
                f"Reviewed report cover and original physical page {page}; CNY; current-period first column; literal {literal}; observed report version only, not all-amendments-complete field",
            )
            f["supersedes"] = predecessor.get((sid, name))
            predecessor[sid, name] = f["record_id"]
            facts.append(f)
            audit.append(
                dict(
                    art_code=art,
                    instrument=instrument,
                    field=name,
                    physical_page=page,
                    source_literal=literal,
                    source_sha256=source["sha256"],
                    review_image=str(image.relative_to(V4)),
                    review_image_sha256=sha(image),
                    known_at=str(known),
                    supersedes=f["supersedes"],
                    independent_human_review=False,
                )
            )
    finance = FactStore(facts)
    finance.to_parquet(V4 / "normalized/financial_reviewed_facts.parquet")
    pd.DataFrame(audit).to_csv(
        PUBLIC / "financial_source_page_reviews.csv", index=False
    )
    states = []
    for art, instrument, date, clause in REMOVALS:
        doc = json.loads(baseline(f"documents/retirement/{art}.json").read_text())
        source = doc["source"]
        pub = doc["announcement"]["notice_date"][:10]
        states.append(
            fact(
                inv.loc[instrument].security_id,
                "listed",
                False,
                date,
                cal.publication_time(pub),
                art,
                source,
                doc["announcement"]["index_sha256"],
                "bool",
                f"Original scanned physical page 1: {clause}; permanent closure of this A-share episode only; later relisting needs separate evidence",
            )
        )
    FactStore(states).to_parquet(V4 / "normalized/status_reviewed_facts.parquet")
    pd.DataFrame(
        [
            dict(
                instrument=i,
                art_code=a,
                removal_date=d,
                physical_page=1,
                exact_clause=c,
                independent_human_review=False,
            )
            for a, i, d, c in REMOVALS
        ]
    ).to_csv(PUBLIC / "removal_source_page_reviews.csv", index=False)
    # These aliases describe disclosures, never an executable exchange-code interval.
    aliases = []
    for r in pd.read_parquet(V4 / "normalized/retired_equity_links.parquet").to_dict(
        "records"
    ):
        doc = original_document(r["art_code"], r["source_sha256"])
        source = doc["source"]
        if source["sha256"] != r["source_sha256"]:
            raise ValueError("alias original source changed")
        aliases.append(
            fact(
                r["security_id"],
                "identity:retired_disclosure_code",
                r["retired_code"],
                r["notice_date"],
                r["known_at"],
                r["art_code"],
                source,
                r["index_sha256"],
                "disclosure_code",
                "Original explicit old A-share / retirement confirmation code link; no account delivery, market order eligibility, first trade, or terminal wealth attested",
            )
        )
    FactStore(aliases).to_parquet(V4 / "normalized/alias_facts.parquet")
    sid = inv.loc["SZ002680"].security_id
    field = "financial:reviewed_reported_operating_cash_flow:2018-12-31"
    replay = []
    for time, expected in [
        ("2019-12-31 15:00", None),
        ("2020-11-23 15:00", None),
        ("2020-11-24 09:30", -203122781.04),
    ]:
        value = finance.get_asof(sid, field, time).value
        if (
            value != expected
            or finance.get_asof(sid, field, time, mode="archived").value is not None
        ):
            raise ValueError("delayed disclosure or historical archive leaked")
        replay.append(
            dict(decision_time=time, historical_value=value, archived_value=None)
        )
    early = FactStore([f for f in facts if stamp(f["known_at"]) < stamp("2021-05-26")])
    sid2 = inv.loc["SH600687"].security_id
    field2 = "financial:reviewed_reported_net_profit_parent:2020-12-31"
    if (
        early.get_asof(sid2, field2, "2021-05-20 15:00").value
        != finance.get_asof(sid2, field2, "2021-05-20 15:00").value
    ):
        raise ValueError("future revision deletion changed early value")
    write_json(
        PUBLIC / "reviewed_fact_summary.json",
        dict(
            financial_facts=len(facts),
            financial_versions=3,
            financial_fields=5,
            new_source_reviewed_removal_facts=len(states),
            alias_facts=len(aliases),
            delayed_report_replay=replay,
            future_revision_deletion_invariant=True,
            all_amendments_complete_claimed=False,
            independent_human_review=False,
            transform_sha256=VERSION,
        ),
    )


if __name__ == "__main__":
    build()
