"""Five BSE exit dates reviewed against archived issuer originals, not name suffixes."""

import json
import re
import pandas as pd
from pypdf import PdfReader
from archive import sha
from backfill_rpc import V2, PUBLIC

SPECS = [
    (
        "832317",
        "2022-04-26",
        "2022-04-25",
        "2022年4月26日在北交所终止上市",
        "TRANSFER_OUT",
    ),
    (
        "833874",
        "2022-07-18",
        "2022-07-15",
        "2022年7月18日在北交所终止上市",
        "TRANSFER_OUT",
    ),
    (
        "833994",
        "2022-07-25",
        "2022-07-22",
        "2022年7月25日起在北交所终止上市",
        "TRANSFER_OUT",
    ),
    (
        "920305",
        "2026-07-30",
        "2026-07-29",
        "2026年7月30日被北京证券交易所终止上市并摘牌",
        "DELISTED_TERMINAL_RIGHTS_UNKNOWN",
    ),
    (
        "920680",
        "2026-01-05",
        "2025-12-31",
        "2026年1月5日被北京证券交易所终止上市并摘牌",
        "DELISTED_TERMINAL_RIGHTS_UNKNOWN",
    ),
]


def main():
    rows = []
    for code, effective, release, clause, kind in SPECS:
        source = json.loads((V2 / f"documents/bse_exit_{code}.json").read_text())
        if sha(source["archive_path"]) != source["sha256"]:
            raise ValueError("original exit notice changed")
        text = re.sub(
            r"\s+", "", PdfReader(source["archive_path"]).pages[0].extract_text()
        )
        if clause not in text:
            raise ValueError("exact reviewed exit clause absent")
        index = json.loads((V2 / f"documents/bse_exit_index_{code}.json").read_text())
        article = source["url"].split("H2_")[1].split("_1.pdf")[0]
        a = next(x for x in index["items"] if x["art_code"] == article)
        if a["notice_date"][:10] != release:
            raise ValueError("exit publication date mismatch")
        rows.append(
            dict(
                instrument="BJ" + code,
                delist_date=pd.Timestamp(effective),
                first_release_date=release,
                exit_kind=kind,
                source_uri=source["url"],
                source_sha256=source["sha256"],
                index_source_sha256=index["sha256"],
                source_path=source["archive_path"],
                source_observed_at=source["source_observed_at"],
                ingested_at=source["ingested_at"],
                physical_page=1,
                exact_clause=clause,
                quality_tier="PIT-reconstructed",
                terminal_cash_and_successor_settlement="UNKNOWN_NOT_ZERO",
            )
        )
    f = pd.DataFrame(rows)
    (V2 / "identity").mkdir(exist_ok=True)
    f.to_parquet(V2 / "identity/bse_exits.parquet", index=False)
    f.drop(columns=["source_path"]).to_csv(
        PUBLIC / "bse_reviewed_exit_dates.csv", index=False
    )


if __name__ == "__main__":
    main()
