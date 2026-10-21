"""One real, issuer-document-based original/correction reconstruction, not blanket certification."""

import json
import re
import pandas as pd
from pypdf import PdfReader
from archive import EP, TOPIC, CACHE, sha, write_json, verify_receipt
from pit import Calendar, COLUMNS, FactStore

FIELD = "financial:other_receivables_intercompany_balance:2023-12-31"


def main():
    records = [
        json.loads(x)
        for x in (EP / "outputs/audits/source_attempts.jsonl").read_text().splitlines()
    ]
    latest = {r["source_id"]: r for r in records}
    names = ["cninfo_first_report_original_pdf", "cninfo_correction_original_pdf"]
    if not all(
        name in latest and latest[name]["status"] != "BLOCKED" for name in names
    ):
        write_json(
            EP / "outputs/audits/financial_vintage_example.json",
            {"status": "BLOCKED", "reason": "MISSING_ORIGINAL_OR_CORRECTION_DOCUMENT"},
        )
        return
    original, correction = [latest[n] for n in names]
    if not all(verify_receipt(r) for r in [original, correction]):
        raise ValueError("financial source hash mismatch")
    first_index = latest["cninfo_first_report_query"]
    correction_index = latest["cninfo_vintage_query"]
    if not all(verify_receipt(r) for r in [first_index, correction_index]):
        raise ValueError("publication index evidence hash mismatch")
    # Only this pre-specified row is extracted; no favorable model outcomes are consulted.
    facts = []
    inv = pd.read_parquet(CACHE / "identity/security_inventory.parquet")
    security = inv[inv.instrument.eq("SZ000584")].iloc[0].security_id
    cal = Calendar(
        pd.read_csv(
            TOPIC / "data/qlib/cn_data_pit_largecap/calendars/day.txt", header=None
        )[0]
    )
    pages = []
    for i, (source, expected, release) in enumerate(
        [
            (original, "91,685,852.54", "2024-04-30"),
            (correction, "37,014,048.62", "2024-07-31"),
        ]
    ):
        pdf = PdfReader(source["archive_path"])
        matches = []
        for j, page in enumerate(pdf.pages):
            text = page.extract_text()
            pattern = r"往来款\s+" + re.escape(expected)
            if re.search(pattern, text):
                matches.append(j + 1)
        if len(matches) != 1:
            raise ValueError("ambiguous or missing financial row extraction")
        page = matches[0]
        pages.append(page)
        f = dict.fromkeys(COLUMNS)
        record_id = "SZ000584_2023_intercompany_" + (
            "original" if i == 0 else "correction"
        )
        f.update(
            record_id=record_id,
            logical_key=security + "/" + FIELD,
            security_id=security,
            field=FIELD,
            value=float(expected.replace(",", "")),
            event_time="2023-12-31",
            effective_time="2023-12-31",
            known_at=cal.publication_time(release),
            source_observed_at=source["source_observed_at"],
            ingested_at=source["ingested_at"],
            source_uri=source["url"],
            source_path=source["archive_path"],
            source_sha256=source["sha256"],
            unit="CNY",
            original_version=source["url"].split("/")[-1],
            transform_sha256=sha(__file__),
            quality_tier="PIT-reconstructed",
            publication_evidence=json.dumps(
                {
                    "publication_date": release,
                    "date_only_next_session": True,
                    "index_sha256": (first_index if i == 0 else correction_index)[
                        "sha256"
                    ],
                    "issuer_correction_confirms_original_release": "2024-04-30",
                    "pdf_page": page,
                }
            ),
            reconstruction=f"Issuer PDF physical page {page}; row 往来款; 期末账面余额; CNY; preserve predecessor",
            supersedes=None if i == 0 else "SZ000584_2023_intercompany_original",
        )
        facts.append(f)
    store = FactStore(facts)
    path = CACHE / "vintages/facts.parquet"
    store.to_parquet(path)
    values = {}
    for t in [
        "2024-04-30 15:00",
        "2024-05-06 15:00",
        "2024-07-31 15:00",
        "2024-08-01 15:00",
    ]:
        r = store.get_asof(security, FIELD, t)
        values[t] = {"value": r.value, "status": r.status, "reason": r.reason}
    assert values["2024-04-30 15:00"]["value"] is None
    assert values["2024-05-06 15:00"]["value"] == 91685852.54
    assert values["2024-07-31 15:00"]["value"] == 91685852.54
    assert values["2024-08-01 15:00"]["value"] == 37014048.62
    truncated = FactStore([facts[0]])
    assert truncated.get_asof(security, FIELD, "2024-07-31 15:00") == store.get_asof(
        security, FIELD, "2024-07-31 15:00"
    )
    assert store.get_asof(security, FIELD, "2024-08-01", mode="archived").value is None
    write_json(
        EP / "outputs/audits/financial_vintage_example.json",
        dict(
            status="PARTIAL_SINGLE_FIELD_PIT_RECONSTRUCTION",
            security_id=security,
            instrument="SZ000584",
            field=FIELD,
            original_source=original["url"],
            correction_source=correction["url"],
            original_sha256=original["sha256"],
            correction_sha256=correction["sha256"],
            original_physical_page=pages[0],
            correction_physical_page=pages[1],
            facts_path=str(path),
            facts_sha256=sha(path),
            values=values,
            time_truncation_invariant=True,
            archived_2024_unavailable=True,
            independent_human_review=False,
            scope="one financial note item; no whole-statement or population certification",
        ),
    )
    print("real financial original/correction replay passed", flush=True)


if __name__ == "__main__":
    main()
