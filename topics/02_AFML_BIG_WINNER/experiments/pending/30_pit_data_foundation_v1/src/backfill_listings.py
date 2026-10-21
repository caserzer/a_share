"""Archive issuer listing announcements; never infer BSE membership from first price."""

import json
import re
import pandas as pd
from pypdf import PdfReader
from archive import sha, write_json, append_receipt
from backfill_rpc import V2, PUBLIC
from backfill_http import CapturedHTTP
from backfill_documents import clean_title


def explicit_listing_dates(text):
    text = re.sub(r"\s+", "", text)
    date = r"(20\d{2})年(\d{1,2})月(\d{1,2})日"
    patterns = [
        r"上市日期[：:]?" + date,
        r"上市时间[：:]?" + date,
        r"(?:将于|自|于)" + date + r"[起在]*北京证券交易所上市",
        r"在北京证券交易所(?:的)?上市(?:日期|时间)[为：:]*" + date,
    ]
    dates = set()
    for pattern in patterns:
        for m in re.finditer(pattern, text):
            d = pd.Timestamp(int(m[1]), int(m[2]), int(m[3]))
            if pd.Timestamp("2021-11-15") <= d <= pd.Timestamp("2026-10-21"):
                dates.add(str(d.date()))
    return dates


def main():
    inv = pd.read_parquet(V2 / "inventory/securities.parquet")
    ipo = pd.read_parquet(V2 / "acquired/bse_ipo.parquet")
    ipo["instrument"] = "BJ" + ipo.SECURITY_CODE
    ipo = ipo.set_index("instrument")
    annual = pd.read_parquet(V2 / "financials/bse_listing_assertions.parquet")
    dates = (
        annual[~annual.listing_date_conflict]
        .drop_duplicates("instrument")
        .set_index("instrument")
        .listing_date.to_dict()
    )
    http = CapturedHTTP()
    records = []
    for row in inv[inv.exchange.eq("BJ")].itertuples():
        path = V2 / f"documents/listings/{row.instrument}.json"
        if path.exists():
            cached = json.loads(path.read_text())
            if (
                cached["status"] == "ORIGINAL_LISTING_NOTICE_MATCHED"
                or cached.get("attempt_version") == 2
            ):
                records.append(cached)
                continue
        target = dates.get(row.instrument)
        if not target and row.instrument in ipo.index:
            d = ipo.loc[row.instrument, "SELECT_LISTING_DATE"]
            if pd.notna(d):
                target = str(max(pd.Timestamp(d), pd.Timestamp("2021-11-15")).date())
        if not target:
            continue
        r = dict(
            instrument=row.instrument,
            security_id=row.security_id,
            target_date=target,
            status="UNRESOLVED",
            quality_tier="UNKNOWN",
            attempt_version=2,
        )
        try:
            day = pd.Timestamp(target)
            params = dict(
                sr=-1,
                page_size=100,
                page_index=1,
                ann_type="A",
                client_source="web",
                stock_list=row.instrument[2:],
                begin_time=str((day - pd.Timedelta(days=35)).date()),
                end_time=str((day + pd.Timedelta(days=7)).date()),
            )
            announcements = []
            index_hashes = []
            page = 1
            while True:
                body, index = http.fetch(
                    "BSE_original_listing_mirror_index_" + row.instrument,
                    "https://np-anotice-stock.eastmoney.com/api/security/ann",
                    params={**params, "page_index": page},
                )
                data = json.loads(body)
                if data.get("success") != 1:
                    raise ValueError("unsuccessful original issuer document index")
                data = data.get("data") or {}
                batch = data.get("list") or []
                announcements.extend(batch)
                index_hashes.append(index["sha256"])
                total = int(data.get("total_hits") or 0)
                if len(announcements) >= total:
                    break
                if not batch or page >= 10:
                    raise ValueError("incomplete original issuer document index")
                page += 1
            r.update(
                index_sha256=index_hashes,
                index_rows=len(announcements),
                reported_total=total,
                document_source="ISSUER_ORIGINAL_PDF_MIRRORED_BY_EASTMONEY",
            )
            candidates = []
            for a in announcements:
                title = clean_title(a["title"])
                if row.instrument[2:] not in [c["stock_code"] for c in a["codes"]]:
                    continue
                if "上市" not in title or any(
                    k in title
                    for k in [
                        "辅导",
                        "限售",
                        "解除",
                        "转让",
                        "转板",
                        "发行结果",
                        "招股",
                        "保荐",
                        "法律意见",
                    ]
                ):
                    continue
                if (
                    "上市公告书" in title
                    or ("上市提示性公告" in title and "北京证券交易所" in title)
                    or (target == "2021-11-15" and "北京证券交易所上市" in title)
                ):
                    candidates.append(a)
            for a in sorted(
                candidates,
                key=lambda x: (
                    "提示性公告" not in x["title"],
                    x["notice_date"],
                    x["art_code"],
                ),
            )[:3]:
                url = "https://pdf.dfcfw.com/pdf/H2_" + a["art_code"] + "_1.pdf"
                pdfbody, pdf = http.fetch("BSE_listing_pdf_" + row.instrument, url)
                if not pdfbody.startswith(b"%PDF"):
                    continue
                reader = PdfReader(pdf["archive_path"])
                matches = []
                for j, page in enumerate(reader.pages[:60]):
                    text = page.extract_text() or ""
                    if "北京证券交易所" not in re.sub(r"\s+", "", text):
                        continue
                    if target in explicit_listing_dates(text):
                        matches.append(j + 1)
                if not matches:
                    continue
                pub = pd.Timestamp(a["notice_date"])
                # Original event evidence is retained. Publication timeline/code intervals still require review.
                r.update(
                    status="ORIGINAL_LISTING_NOTICE_MATCHED",
                    listing_date=target,
                    quality_tier="Historical-proxy",
                    first_release_date=str(pub.date()),
                    first_version_certified=False,
                    known_at_rule="date_only_next_verified_session_open",
                    source_uri=url,
                    source_path=pdf["archive_path"],
                    source_sha256=pdf["sha256"],
                    physical_pages=matches,
                    title=clean_title(a["title"]),
                    announcement_id=a["art_code"],
                    printed_index_code=row.instrument[2:],
                    historical_code_status="TODAY_INDEX_CODE_REWRITTEN_ORIGINAL_PDF_CODE_RETAINED",
                    org_id=row.org_id,
                    observed_at=pdf["source_observed_at"],
                    transform_sha256=sha(__file__),
                )
                break
        except PermissionError:
            raise
        except Exception as exc:
            r["reason"] = type(exc).__name__ + ": " + str(exc)[:200]
        write_json(path, r)
        records.append(r)
        append_receipt(PUBLIC / "listing_document_progress.jsonl", r)
        print("listing", len(records), row.instrument, r["status"], flush=True)
    f = pd.DataFrame(records)
    f.drop(columns=["source_path"], errors="ignore").to_csv(
        PUBLIC / "bse_original_listing_notices.csv", index=False
    )
    write_json(
        PUBLIC / "listing_document_summary.json",
        dict(
            queried=len(f),
            original_listing_notices=int(
                f.status.eq("ORIGINAL_LISTING_NOTICE_MATCHED").sum()
            ),
            unresolved=int(f.status.ne("ORIGINAL_LISTING_NOTICE_MATCHED").sum()),
        ),
    )


if __name__ == "__main__":
    main()
