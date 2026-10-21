"""Incremental original financial values; unresolved table semantics stay candidates."""

import argparse
import json
import re
import time
from decimal import Decimal
import pandas as pd
from archive import write_json
from v3_core import V3, PUBLIC3, code_version, documents
from v3_evidence import original_pages, printed_security, security_map

MONEY = r"[-−]?(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}"
FIELDS = {
    "revenue": r"营业收入",
    "net_profit_parent": r"归属于(?:上市公司|挂牌公司|两网公司或退市公司)(?:股东|的股东)的净利润",
    "operating_cash_flow": r"经营活动产生的现金流量净额",
    "total_assets": r"(?:总资产|资产总计)",
    "equity_parent": r"归属于(?:上市公司|挂牌公司|两网公司或退市公司)(?:股东|的股东)的净资产",
}
VERSION = code_version(__file__)


def cover_report_year(pages):
    text = "\n".join(pages[:2])
    if "年度报告" not in text:
        return None
    years = set(re.findall(r"(?:^|\n)\s*(20\d{2})\s*(?:\n|年度报告)", text))
    years.update(re.findall(r"(20\d{2})年?年度报告", re.sub(r"\s+", "", text)))
    return int(next(iter(years))) if len(years) == 1 else None


def parse_page(text, year, original_cover_year=None):
    # Separate adjacent numeric columns before removing layout whitespace.
    text = re.sub(r"(?<=\d)\s+(?=[−\-\d])", "|", text)
    text = re.sub(r"\s+", "", text)
    heading = re.search(r"(?:主要)?会计数据[、和及]财务指标", text)
    if not heading or "单位：万元" in text or "单位:万元" in text:
        return []
    region = text[heading.end() :]
    explicit_unit = "单位：元" in text or "单位:元" in text
    found = []
    for field, label in FIELDS.items():
        matches = list(
            re.finditer(label + r"(?:[（(]元[）)])?(" + MONEY + r")(?![%\d])", region)
        )
        if len(matches) != 1:
            continue
        m = matches[0]
        years = re.findall(r"(20\d{2})年(?:度|末)?", region[: m.start()])
        current_header = re.search(
            r"(?:本期上年同期|本期期末上年期末)", region[: m.start()]
        )
        if years and int(years[0]) != year:
            continue
        if not years and not (original_cover_year == year and current_header):
            continue
        if not explicit_unit and not re.search(r"[（(]元[）)]", m[0]):
            continue
        found.append(
            dict(
                field=field,
                candidate_value=float(Decimal(m[1].replace(",", "").replace("−", "-"))),
                source_literal=m[1],
                source_label_and_literal=m[0],
                unit="CNY",
                extraction_rule="EXPLICIT_CNY_MAIN_ACCOUNTING_HEADING_REPORT_YEAR_FIRST_COLUMN_UNIQUE_LABEL",
            )
        )
    return found


def parse_available():
    mapping = security_map()
    out = V3 / "parsed/financial" / VERSION
    out.mkdir(parents=True, exist_ok=True)
    for p, r in documents("financial"):
        target = out / p.name
        if target.exists():
            continue
        if r["status"] != "ORIGINAL_PDF_RECOVERED":
            continue
        source, a = r["source"], r["announcement"]
        try:
            pages = original_pages(source["archive_path"], source["sha256"], limit=24)
            printed = printed_security(pages, mapping)
            candidates = []
            if printed == a["security_id"]:
                for i, page in enumerate(pages):
                    for value in parse_page(
                        page,
                        int(a["report_period"][:4]),
                        original_cover_year=cover_report_year(pages),
                    ):
                        candidates.append(dict(**value, physical_page=i + 1))
            # Duplicated same field anywhere in the inspected tables is unreviewed.
            fields = pd.Series(
                [v["field"] for v in candidates], dtype=str
            ).value_counts()
            candidates = [v for v in candidates if fields[v["field"]] == 1]
            result = dict(
                art_code=p.stem,
                security_id=a["security_id"],
                printed_security_id=printed,
                report_period=a["report_period"],
                title=a["title"],
                is_revision=a["is_revision"],
                notice_date=a["notice_date"],
                candidate_known_at=a["known_at"],
                source=source,
                index_sha256=a["index_sha256"],
                candidates=candidates,
                parse_status="CANDIDATES_UNREVIEWED"
                if candidates
                else "NO_UNAMBIGUOUS_MAIN_TABLE_VALUES",
                quality_tier="UNKNOWN/BLOCKED",
                transform_sha256=VERSION,
            )
        except Exception as exc:
            result = dict(
                art_code=p.stem,
                parse_status="UNKNOWN",
                error=str(exc)[:250],
                candidates=[],
            )
        write_json(target, result)
    return out


def aggregate(folder):
    values, docs = [], []
    for p in sorted(folder.glob("*.json")):
        r = json.loads(p.read_text())
        docs.append(
            dict(
                art_code=p.stem,
                parse_status=r["parse_status"],
                candidate_fields=len(r["candidates"]),
            )
        )
        for v in r["candidates"]:
            values.append(
                dict(
                    **v,
                    art_code=p.stem,
                    security_id=r["security_id"],
                    report_period=r["report_period"],
                    title=r["title"],
                    is_revision=r["is_revision"],
                    notice_date=r["notice_date"],
                    candidate_known_at=r["candidate_known_at"],
                    source_sha256=r["source"]["sha256"],
                    source_uri=r["source"]["url"],
                    index_sha256=r["index_sha256"],
                    quality_tier="UNKNOWN/BLOCKED",
                    transform_sha256=VERSION,
                )
            )
    f = pd.DataFrame(values)
    f.to_parquet(
        V3 / "normalized/financial_original_value_candidates.parquet", index=False
    )
    f.to_csv(PUBLIC3 / "financial_original_value_candidates.csv", index=False)
    pd.DataFrame(docs).to_csv(PUBLIC3 / "financial_original_parsing.csv", index=False)
    write_json(
        PUBLIC3 / "financial_parsing_summary.json",
        dict(
            parsed_documents=len(docs),
            original_value_candidates=len(values),
            securities_with_candidates=f.security_id.nunique() if len(f) else 0,
            source_revision_values=int(f.is_revision.sum()) if len(f) else 0,
            candidates_not_promoted_to_pit=True,
            transform_sha256=VERSION,
        ),
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--watch", action="store_true")
    args = p.parse_args()
    while True:
        folder = parse_available()
        aggregate(folder)
        if not args.watch or (PUBLIC3 / "financial_document_summary.json").exists():
            break
        print("financial parsed", len(list(folder.glob("*.json"))), flush=True)
        time.sleep(20)


if __name__ == "__main__":
    main()
