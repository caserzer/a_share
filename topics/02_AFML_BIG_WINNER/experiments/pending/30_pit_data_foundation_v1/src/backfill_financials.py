"""Deterministic, conservative extraction from newly archived original reports.

Values remain diagnostic candidates until their table/issuer/year has been reviewed.
Listing dates are issuer assertions; original listing notices are recovered separately.
"""

import json
import re
from decimal import Decimal
import pandas as pd
from pypdf import PdfReader
from archive import sha, write_json
from backfill_rpc import V2, PUBLIC

FIELDS = {
    "revenue": r"营业收入",
    "net_profit_parent": r"归属于上市公司股东的净利润",
    "operating_cash_flow": r"经营活动产生的现金流量净额",
    "total_assets": r"(?:总资产|资产总计)",
    "equity_parent": r"归属于上市公司股东的净资产",
}
MONEY = r"[-−]?(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}"


def parse_main_page(text, year):
    text = re.sub(r"(?<=\d)\s+(?=[−\-\d])", "|", text)
    text = re.sub(r"\s+", "", text)
    heading = re.search(r"(?:主要)?会计数据[、和]财务指标", text)
    if not heading:
        return []
    if "单位：万元" in text or "单位:万元" in text:
        return []
    explicit_page_unit = "单位：元" in text or "单位:元" in text
    region = text[heading.end() :]
    values = []
    for field, label in FIELDS.items():
        pattern = label + r"(?:[（(]元[）)])?(" + MONEY + r")(?![%\d])"
        matches = list(re.finditer(pattern, region))
        if len(matches) != 1:
            continue
        match = matches[0]
        raw_label = match.group(0)
        if not explicit_page_unit and not re.search(r"[（(]元[）)]", raw_label):
            continue
        years = re.findall(r"(20\d{2})年(?:度|末)?", region[: match.start()])
        if not years or int(years[0]) != year:
            continue
        number = match.group(1).replace(",", "").replace("−", "-")
        values.append(
            dict(
                field=field,
                value=float(Decimal(number)),
                unit="CNY",
                source_literal=match.group(1),
                report_period=f"{year}-12-31",
                rule="main_data_heading_explicit_CNY_latest_year_first_column_unique_label",
            )
        )
    return values


def parse_bse_listing(text):
    text = re.sub(r"\s+", "", text)
    if not re.search(r"(?:公司)?股票上市交易所北京证券交易所", text):
        return None
    m = re.search(r"上市时间(20\d{2})[年/.-](\d{1,2})[月/.-](\d{1,2})", text)
    if not m:
        return None
    d = pd.Timestamp(int(m[1]), int(m[2]), int(m[3]))
    if d < pd.Timestamp("2021-11-15"):
        return None
    return str(d.date())


def main():
    records = []
    values = []
    listings = []
    for p in sorted((V2 / "documents/financial").glob("*.json")):
        r = json.loads(p.read_text())
        if r["status"] != "ORIGINAL_DOCUMENT_RECOVERED":
            continue
        if sha(r["source_path"]) != r["source_sha256"]:
            raise ValueError("changed original PDF")
        if (r.get("reported_total") or 0) > r["index_rows"]:
            r["original_vintage_status"] = "INCOMPLETE_INDEX_FIRST_VERSION_UNPROVEN"
        else:
            r["original_vintage_status"] = "ORIGINAL_YEAR_INDEX_AND_PDF_RETAINED"
        doc = PdfReader(r["source_path"])
        candidates = []
        for j, page in enumerate(doc.pages[:24]):
            text = page.extract_text() or ""
            date = parse_bse_listing(text)
            if date and r["instrument"].startswith("BJ"):
                listings.append(
                    dict(
                        instrument=r["instrument"],
                        security_id=r["security_id"],
                        listing_date=date,
                        physical_page=j + 1,
                        source_uri=r["source_uri"],
                        source_sha256=r["source_sha256"],
                        source_path=r["source_path"],
                        first_release_date=r["first_release_date"],
                        quality_tier="Historical-proxy",
                        reason="LATER_ORIGINAL_ANNUAL_REPORT_ASSERTS_LISTING_DATE_ORIGINAL_LISTING_NOTICE_PENDING",
                    )
                )
            for item in parse_main_page(text, int(r["report_year"])):
                candidates.append(dict(**item, physical_page=j + 1))
        for item in candidates:
            if sum(x["field"] == item["field"] for x in candidates) != 1:
                continue
            values.append(
                dict(
                    **item,
                    instrument=r["instrument"],
                    security_id=r["security_id"],
                    first_release_date=r["first_release_date"],
                    source_uri=r["source_uri"],
                    source_path=r["source_path"],
                    source_sha256=r["source_sha256"],
                    index_source_sha256=r["index_source_sha256"],
                    original_vintage_status=r["original_vintage_status"],
                    quality_tier="Historical-proxy",
                    transform_sha256=sha(__file__),
                    review_status="COLUMN_UNIT_AND_PERIOD_REVIEW_REQUIRED_NO_AUTO_CERTIFICATION",
                )
            )
        r.pop("extractions", None)
        records.append(r)
    out = V2 / "financials"
    out.mkdir(exist_ok=True)
    f = pd.DataFrame(values)
    f.to_parquet(out / "original_extraction_candidates.parquet", index=False)
    f.drop(columns=["source_path"], errors="ignore").to_csv(
        PUBLIC / "financial_extraction_candidates.csv", index=False
    )
    q = pd.DataFrame(listings)
    if not q.empty:
        conflicts = q.groupby("instrument").listing_date.nunique().gt(1)
        q["listing_date_conflict"] = q.instrument.map(conflicts)
    q.to_parquet(out / "bse_listing_assertions.parquet", index=False)
    q.drop(columns=["source_path"], errors="ignore").to_csv(
        PUBLIC / "bse_listing_assertions.csv", index=False
    )
    pd.DataFrame(records).drop(columns=["source_path"], errors="ignore").to_csv(
        PUBLIC / "financial_original_documents.csv", index=False
    )
    write_json(
        PUBLIC / "financial_normalization.json",
        dict(
            original_documents=len(records),
            extraction_candidate_values=len(f),
            companies_with_candidate_values=int(f.instrument.nunique())
            if len(f)
            else 0,
            BSE_listing_date_assertions=int(q.instrument.nunique()) if len(q) else 0,
            original_vintage_and_raw_values_not_auto_certified=True,
        ),
    )
    print(
        "original documents",
        len(records),
        "financial candidates",
        len(f),
        "listing dates",
        q.instrument.nunique() if len(q) else 0,
        flush=True,
    )


if __name__ == "__main__":
    main()
