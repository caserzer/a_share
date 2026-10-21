"""Three explicit pixel-page reviews of scanned retired-equity confirmations."""

from archive import sha, write_json
from v3_core import V3, PUBLIC3, documents, code_version
from v3_evidence import security_map, calendar

CASES = [
    (
        "AN201901071282709522",
        "000979",
        "400071",
        "2019-01-07",
        "6e74b72d95eb069573fbe1ac094df977dc32738905ef24b724363b3c845a392c",
    ),
    (
        "AN201907151338660285",
        "002070",
        "400072",
        "2019-07-15",
        "967a4bad925aaa8888980bb13251c34e4029b8ecd883c884b49169cc29c72f68",
    ),
    (
        "AN201907191339857565",
        "600401",
        "400074",
        "2019-07-19",
        "fadc25d56aadd5ce3880841627753be07b98b04363756e9cf93ee1de1b8b3c4b",
    ),
]


def build():
    records = {p.stem: r for p, r in documents("retirement")}
    mapping, cal, output = security_map(), calendar(), []
    for art, old, new, date, expected in CASES:
        r = records[art]
        if (
            r["source"]["sha256"] != expected
            or sha(r["source"]["archive_path"]) != expected
        ):
            raise ValueError("pixel-reviewed scanned original changed")
        if r["announcement"]["notice_date"][:10] != date or len(mapping[old]) != 1:
            raise ValueError("reviewed old issuer or publication changed")
        images = []
        for page in [1, 2]:
            image = V3 / f"reviews/retirement/{art}_page{page}.png"
            if not image.exists():
                raise ValueError("reviewed page raster not retained")
            images.append(
                dict(
                    physical_page=page,
                    path=str(image.relative_to(V3)),
                    sha256=sha(image),
                )
            )
        output.append(
            dict(
                art_code=art,
                security_id=next(iter(mapping[old])),
                old_code=old,
                retired_code=new,
                notice_date=date,
                known_at=str(cal.publication_time(date)),
                source_sha256=expected,
                source_uri=r["source"]["url"],
                index_sha256=r["announcement"]["index_sha256"],
                physical_page=1,
                physical_pages="[1, 2]",
                images=images,
                exact_clause=f"Pixel page 1: 股票代码 {old}; pixel page 2: 确权证券代码 {new}",
                legal_equity_continuity_evidence=True,
                actual_transfer_or_sale_proven=False,
                review_method="AGENT_VISUAL_REVIEW_OF_ORIGINAL_SCANNED_PAGES_NOT_OCR_AUTOPROMOTION",
                independent_human_review=False,
                transform_sha256=code_version(__file__),
            )
        )
    write_json(V3 / "reviewed/scanned_equity_links.json", output)
    write_json(PUBLIC3 / "scanned_equity_source_page_reviews.json", output)


if __name__ == "__main__":
    build()
