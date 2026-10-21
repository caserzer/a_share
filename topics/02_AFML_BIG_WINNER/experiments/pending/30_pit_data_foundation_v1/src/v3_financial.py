"""Complete issuer/alias disclosure indices and append-only financial report chains."""

import argparse
import json
import re
import pandas as pd
from archive import write_json, append_receipt
from v3_core import V3, PUBLIC3, V2_RELEASE, Capture, code_version
from v3_announcements import acquire_index, financial_cohort, clean
from v3_evidence import security_map, calendar


def classify_report(title):
    t = clean(title)
    years = set(re.findall(r"(20\d{2})(?:年|年度)", t))
    if len(years) != 1:
        return None
    year = next(iter(years))
    if any(x in t for x in ["第一季度", "一季度"]):
        end = "03-31"
    elif any(x in t for x in ["半年度", "半年报", "中期报告"]):
        end = "06-30"
    elif any(x in t for x in ["第三季度", "三季度"]):
        end = "09-30"
    elif any(x in t for x in ["年度报告", "年度财务报告", "年度财务报表", "年报"]):
        end = "12-31"
    else:
        return None
    before_copy = any(x in t for x in ["更正前", "修订前", "更新前"])
    revision = not before_copy and any(x in t for x in ["更正", "修订", "更新", "补充"])
    if "摘要" in t:
        form = "summary"
    elif any(
        x in t
        for x in [
            "鉴证",
            "审计报告",
            "审阅报告",
            "审计意见",
            "核查",
            "律师",
            "问询",
            "回复",
            "进展",
            "专项说明",
            "风险提示",
            "承诺",
        ]
    ):
        form = "ancillary"
    elif "公告" in t or ("关于" in t and revision):
        form = "amendment_notice" if revision else "ancillary"
    elif any(x in t for x in ["财务报告", "财务报表及附注"]):
        form = "financial_statements"
    else:
        form = "full_report"
    return dict(
        report_period=year + "-" + end,
        form=form,
        is_revision=revision,
        pre_revision_copy_designation=before_copy,
    )


def acquire_aliases(http):
    cohort = financial_cohort()
    aliases = pd.read_parquet(V2_RELEASE / "normalized/code_intervals.parquet")
    aliases = aliases[aliases.security_id.isin(cohort.security_id)]
    old = pd.DataFrame(dict(instrument=sorted(set(aliases.historical_instrument))))
    if len(old):
        acquire_index(http, "financial_aliases_A", old, 1, 1, ann_type="A")
        acquire_index(http, "financial_aliases_SB", old, 1, 1, ann_type="SB")


def build_chains():
    mapping = security_map()
    cal = calendar()
    rows, ambiguous = [], []
    for name in ["financial", "financial_aliases_A", "financial_aliases_SB"]:
        path = V3 / f"indices/{name}_complete.parquet"
        if not path.exists():
            raise ValueError("missing full financial issuer/alias partition: " + name)
        for encoded in pd.read_parquet(path).announcement:
            a = json.loads(encoded)
            ids = set()
            for c in a.get("codes", []):
                ids.update(mapping.get(c["stock_code"], set()))
            kind = classify_report(a["title"])
            if len(ids) != 1 or kind is None:
                ambiguous.append(
                    dict(
                        art_code=a["art_code"],
                        title=a["title"],
                        reason="UNRESOLVED_ISSUER_OR_PERIOD",
                    )
                )
                continue
            rows.append(
                dict(
                    security_id=next(iter(ids)),
                    art_code=a["art_code"],
                    title=a["title"],
                    notice_date=a["notice_date"][:10],
                    known_at=str(cal.publication_time(a["notice_date"][:10])),
                    index_sha256=a["index_sha256"],
                    index_partition=name,
                    **kind,
                )
            )
    f = pd.DataFrame(rows).drop_duplicates(["security_id", "art_code"])
    f = f.sort_values(
        ["security_id", "report_period", "form", "notice_date", "art_code"]
    )
    f["logical_report_key"] = f.security_id + "/" + f.report_period + "/" + f.form
    selected, chains = [], []
    # Report-period pairs that actually have a revision, selected periods from v2,
    # and fixed strata are frozen by rule before reading report values.
    prior = []
    for p in (V2_RELEASE / "acquisition/documents/financial").glob("*.json"):
        r = json.loads(p.read_text())
        if r.get("year"):
            prior.append((r["security_id"], str(r["year"]) + "-12-31"))
    # V2 releases retain the original per-target metadata under acquisition/financial
    # on older layouts; inspect both exact declared layouts without guessing values.
    for folder in [
        "documents/financial",
        "acquisition/financial",
        "acquisition/documents/financial",
    ]:
        for p in (V2_RELEASE / folder).glob("*.json"):
            r = json.loads(p.read_text())
            m = re.search(r"_(20\d{2})$", p.stem)
            if m and r.get("security_id"):
                prior.append((r["security_id"], m[1] + "-12-31"))
    prior = set(prior)
    from v3_core import inventory

    inv = inventory()
    fixed = set(
        inv.loc[
            inv.instrument.isin(
                ["SH600000", "SZ000001", "SZ000584", "SH688001", "BJ920001"]
            ),
            "security_id",
        ]
    )
    for key, g in f.groupby("logical_report_key", sort=True):
        g = g.sort_values(["notice_date", "art_code"])
        original = g[~g.is_revision]
        first_original_date = None if original.empty else original.notice_date.min()
        predecessor = []
        for day, same_day in g.groupby("notice_date", sort=True):
            for r in same_day.to_dict("records"):
                r.update(
                    prior_version_ids=json.dumps(predecessor),
                    original_report_present=first_original_date is not None,
                    first_original_notice_date=first_original_date,
                    same_day_order_ambiguous=len(same_day) > 1,
                    source_index_does_not_certify_numeric_fields=True,
                    version_chain_status="INDEXED_ORIGINAL_AND_REVISIONS"
                    if first_original_date
                    else "ORIGINAL_FIRST_VERSION_MISSING",
                )
                chains.append(r)
            predecessor.extend(same_day.art_code)
        annual = (
            g.iloc[0].report_period.endswith("12-31")
            and "2017" <= g.iloc[0].report_period[:4] <= "2025"
        )
        if not annual or g.iloc[0].form != "full_report":
            continue
        pair = (g.iloc[0].security_id, g.iloc[0].report_period)
        if g.is_revision.any() or pair in prior or g.iloc[0].security_id in fixed:
            selected.extend(g.to_dict("records"))
    result = pd.DataFrame(chains)
    (V3 / "normalized").mkdir(parents=True, exist_ok=True)
    result.to_parquet(V3 / "normalized/financial_version_chains.parquet", index=False)
    result.to_csv(PUBLIC3 / "financial_version_chains.csv", index=False)
    pd.DataFrame(ambiguous).drop_duplicates().to_csv(
        PUBLIC3 / "financial_unresolved_index_rows.csv", index=False
    )
    queue = pd.DataFrame(selected).drop_duplicates("art_code")
    queue.to_csv(PUBLIC3 / "financial_original_queue.csv", index=False)
    write_json(
        PUBLIC3 / "financial_chain_summary.json",
        dict(
            classified_disclosure_rows=len(result),
            logical_report_chains=result.logical_report_key.nunique(),
            revision_rows=int(result.is_revision.sum()),
            annual_original_queue=len(queue),
            v2_selected_periods_detected=len(prior),
            numeric_fields_certified_from_index=0,
            unresolved_issuer_or_period_rows=len(
                pd.DataFrame(ambiguous).drop_duplicates()
            ),
            same_day_order_is_not_invented=True,
            transform_sha256=code_version(__file__),
        ),
    )
    return queue


def acquire_documents(http, queue):
    done = []
    # Genuine original/revision comparisons precede unpaired single report recovery.
    counts = queue.groupby(["security_id", "report_period"]).is_revision.transform(
        "max"
    )
    queue = queue.assign(revision_pair=counts).sort_values(
        ["revision_pair", "security_id", "report_period", "notice_date"],
        ascending=[False, True, True, True],
    )
    for i, row in enumerate(queue.to_dict("records")):
        p = V3 / f"documents/financial/{row['art_code']}.json"
        if p.exists():
            done.append(json.loads(p.read_text())["status"])
            continue
        r = dict(
            announcement=row,
            status="UNKNOWN",
            evidence_kind="FINANCIAL_ORIGINAL_VERSION",
        )
        try:
            body, rec = http.fetch(
                "financial_original_" + row["art_code"],
                "https://pdf.dfcfw.com/pdf/H2_" + row["art_code"] + "_1.pdf",
            )
            if not body.startswith(b"%PDF"):
                raise ValueError("not an original PDF")
            r.update(status="ORIGINAL_PDF_RECOVERED", source=rec)
        except PermissionError:
            raise
        except Exception as exc:
            r["error"] = str(exc)[:250]
        write_json(p, r)
        done.append(r["status"])
        append_receipt(
            PUBLIC3 / "financial_document_progress.jsonl",
            dict(art_code=row["art_code"], status=r["status"]),
        )
        if i % 50 == 0:
            print("financial originals", i + 1, "/", len(queue), flush=True)
    write_json(
        PUBLIC3 / "financial_document_summary.json",
        dict(
            selected=len(queue),
            recovered=done.count("ORIGINAL_PDF_RECOVERED"),
            unresolved=done.count("UNKNOWN"),
        ),
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--index-only", action="store_true")
    a = p.parse_args()
    http = Capture()
    acquire_aliases(http)
    queue = build_chains()
    if not a.index_only:
        acquire_documents(http, queue)


if __name__ == "__main__":
    main()
