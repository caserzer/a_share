"""Recover original financial/termination material for missing-risk and BSE cohorts.

Selection depends on missing coverage and disclosure vintage, never model scores.
Original and correction titles remain separate. No source PDF bytes enter Git.
"""

import argparse
import json
import re
import pandas as pd
from pypdf import PdfReader
from archive import write_json, append_receipt
from backfill_rpc import V2, PUBLIC
from backfill_http import CapturedHTTP


def clean_title(title):
    return re.sub(r"\s+", "", re.sub("<[^>]+>", "", title))


def select_original(announcements, code, year):
    rows = []
    for a in announcements:
        title = clean_title(a["announcementTitle"])
        if a["secCode"] != code:
            continue
        if str(year) not in title or "年度报告" not in title:
            continue
        if any(
            word in title
            for word in [
                "摘要",
                "更正",
                "更新",
                "修订",
                "说明",
                "审核",
                "问询",
                "决议",
                "提示",
                "取消",
                "关于",
            ]
        ):
            continue
        rows.append(a)
    return sorted(rows, key=lambda a: (a["announcementTime"], a["announcementId"]))


def extract_main_data(path, year):
    """Conservative original-report extraction: explicit units + current-year first column."""
    pdf = PdfReader(path)
    labels = {
        "revenue": r"营业收入[（(]元[）)]",
        "net_profit_parent": r"归属于上市公司股东的净利润[（(]元[）)]",
        "operating_cash_flow": r"经营活动产生的现金流量净额[（(]元[）)]",
        "total_assets": r"总资产[（(]元[）)]",
        "equity_parent": r"归属于上市公司股东的净资产[（(]元[）)]",
    }
    extracted = []
    number = r"[-−]?(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}"
    for j, page in enumerate(pdf.pages[:24]):
        text = re.sub(r"\s+", "", page.extract_text() or "")
        if not any(
            k in text
            for k in ["主要会计数据", "主要财务指标", "主要会计数据和财务指标"]
        ):
            continue
        if str(year) + "年" not in text:
            continue
        # Require the latest year heading before any supported financial row.
        for field, label in labels.items():
            matches = list(re.finditer(label + r"(" + number + r")", text))
            if len(matches) != 1:
                continue
            m = matches[0]
            headers = [
                x.group(0)
                for x in re.finditer(r"20\d{2}年(?:度|末)?", text[: m.start()])
            ]
            if not headers or not any(h.startswith(str(year)) for h in headers):
                continue
            value = float(m.group(1).replace(",", "").replace("−", "-"))
            extracted.append(
                dict(
                    field=field,
                    value=value,
                    unit="CNY",
                    report_period=f"{year}-12-31",
                    physical_page=j + 1,
                    extraction_rule="unique_explicit_CNY_label_first_numeric_value_on_main_data_page",
                    quality_tier="Historical-proxy",
                    review_status="EXTRACTION_CANDIDATE_REQUIRES_COLUMN_AND_PERIOD_REVIEW",
                )
            )
    # A repeated field/page is ambiguous; preserve candidates but do not publish a selected value.
    counts = {
        r["field"]: sum(x["field"] == r["field"] for x in extracted) for r in extracted
    }
    return [r for r in extracted if counts[r["field"]] == 1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int)
    args = p.parse_args()
    inv = pd.read_parquet(V2 / "inventory/securities.parquet")
    selected = inv[
        (inv.exchange.eq("BJ"))
        | (inv.is_delisted.eq(True) & inv.delist_date.ge(pd.Timestamp("2017-01-03")))
    ].sort_values("instrument")
    if args.limit:
        selected = selected.head(args.limit)
    http = CapturedHTTP()
    records = []
    extractions = []
    for row in selected.itertuples():
        year = (
            2025
            if row.exchange == "BJ" or pd.isna(row.delist_date)
            else min(2025, row.delist_date.year - 1)
        )
        resultpath = V2 / f"documents/financial/{row.instrument}_{year}.json"
        if resultpath.exists():
            r = json.loads(resultpath.read_text())
            records.append(r)
            extractions.extend(r.get("extractions", []))
            continue
        record = dict(
            instrument=row.instrument,
            security_id=row.security_id,
            report_year=year,
            selection_rule="missing_BSE_financials_or_last_full_fiscal_year_before_delisting",
            status="UNRESOLVED",
        )
        try:
            code = row.instrument[2:]
            org = getattr(row, "org_id", None)
            if pd.isna(org):
                org = None
            if not org and row.exchange in ["SZ", "SH"]:
                # This is only a query candidate. A matching returned secCode is required.
                org = ("gssz0" if row.exchange == "SZ" else "gssh0") + code
            if not org:
                raise ValueError("missing public issuer identifier")
            payload = dict(
                pageNum=1,
                pageSize=100,
                tabName="fulltext",
                column="szse",
                stock=f"{code},{org}",
                searchkey=f"{year}年年度报告",
                seDate=f"{year + 1}-01-01~{min(str(year + 1) + '-12-31', '2026-10-21')}",
                isHLtitle="true",
                sortName="time",
                sortType="asc",
            )
            body, index = http.fetch(
                "financial_original_index_" + row.instrument,
                "https://www.cninfo.com.cn/new/hisAnnouncement/query",
                data=payload,
                method="POST",
            )
            data = json.loads(body)
            record.update(
                index_source_sha256=index["sha256"],
                index_rows=len(data.get("announcements") or []),
                reported_total=data.get("totalAnnouncement"),
            )
            if (data.get("totalAnnouncement") or 0) > len(
                data.get("announcements") or []
            ):
                raise ValueError(
                    "index pagination required; no first-vintage selection from truncated index"
                )
            candidates = select_original(data.get("announcements") or [], code, year)
            if not candidates:
                raise ValueError(
                    "no matching original full annual report in complete issuer/year index"
                )
            # Corrections/updates stay in the index, but never replace the earliest original.
            a = candidates[0]
            url = "https://static.cninfo.com.cn/" + a["adjunctUrl"]
            pdfbody, pdf = http.fetch("financial_original_pdf_" + row.instrument, url)
            if not pdfbody.startswith(b"%PDF"):
                raise ValueError("non-PDF source rejected")
            pub = pd.to_datetime(a["announcementTime"], unit="ms", utc=True).tz_convert(
                "Asia/Shanghai"
            )
            record.update(
                status="ORIGINAL_DOCUMENT_RECOVERED",
                announcement_id=a["announcementId"],
                title=clean_title(a["announcementTitle"]),
                first_release_date=str(pub.date()),
                precise_release_time_certified=False,
                source_uri=url,
                source_sha256=pdf["sha256"],
                source_path=pdf["archive_path"],
                observed_at=pdf["source_observed_at"],
                known_at_rule="date_only_next_verified_session_open",
                historical_original_evidence="issuer_year_complete_index_plus_preserved_earliest_non_revised_full_report",
                independent_human_review=False,
            )
            items = extract_main_data(pdf["archive_path"], year)
            for item in items:
                item.update(
                    instrument=row.instrument,
                    source_sha256=pdf["sha256"],
                    source_uri=url,
                    first_release_date=str(pub.date()),
                )
            record["extractions"] = items
            extractions.extend(items)
            print(
                "original financial",
                row.instrument,
                year,
                "pages",
                len(PdfReader(pdf["archive_path"]).pages),
                "candidates",
                len(items),
                flush=True,
            )
        except PermissionError as exc:
            record.update(status="BLOCKED_PERMISSION", error=str(exc))
            write_json(resultpath, record)
            raise
        except Exception as exc:
            record["error"] = type(exc).__name__ + ": " + str(exc)[:250]
            print("financial gap", row.instrument, str(exc)[:90], flush=True)
        write_json(resultpath, record)
        records.append(record)
        append_receipt(PUBLIC / "financial_document_progress.jsonl", record)
    pd.DataFrame(
        [{k: v for k, v in r.items() if k != "extractions"} for r in records]
    ).to_csv(PUBLIC / "financial_original_documents.csv", index=False)
    pd.DataFrame(extractions).to_csv(
        PUBLIC / "financial_extraction_candidates.csv", index=False
    )
    write_json(
        PUBLIC / "financial_document_summary.json",
        dict(
            queried=len(records),
            original_documents=sum(
                r["status"] == "ORIGINAL_DOCUMENT_RECOVERED" for r in records
            ),
            original_extraction_candidates=len(extractions),
            candidate_values_are_not_certified_model_inputs=True,
            missing=len(
                [r for r in records if r["status"] != "ORIGINAL_DOCUMENT_RECOVERED"]
            ),
            selection="pre_registered_missing_BSE_and_delisted_cohorts",
        ),
    )


if __name__ == "__main__":
    main()
