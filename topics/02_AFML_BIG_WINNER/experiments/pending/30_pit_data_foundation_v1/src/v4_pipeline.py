"""Join retired disclosure aliases, recover annual vintages, retain strict blockers."""

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

from archive import EP, archive_bytes, sha, write_json
from pit import Calendar, stamp
from v3_financial import classify_report as prior_classify_report
from v3_parse_financial import cover_report_year, parse_page
from v4_core import BASE, PUBLIC, V4, Capture, baseline, source_bytes

VERSION = archive_bytes(Path(__file__).read_bytes(), root=V4)[1]


def classify_report(title):
    kind = prior_classify_report(title)
    if kind and any(
        k in title
        for k in [
            "独立意见",
            "独立董事",
            "董事会决议",
            "监事会决议",
            "内部控制",
            "社会责任",
        ]
    ):
        kind["form"] = "ancillary"
    return kind


def calendar():
    return Calendar(
        pd.read_parquet(baseline("baseline/normalized/calendar.parquet")).date
    )


def original_pages(source, limit=24):
    path = source_bytes(source)
    target = V4 / f"text/{source['sha256']}.first_{limit}.json"
    if target.exists():
        r = json.loads(target.read_text())
        if r["source_sha256"] != sha(path):
            raise ValueError("changed PDF text source")
        return r["pages"]
    sys.path.insert(0, str(BASE / "vendor"))
    import pymupdf

    with pymupdf.open(path) as pdf:
        pages = [p.get_text("text", sort=False) for p in pdf[:limit]]
    write_json(
        target,
        dict(
            source_sha256=sha(path),
            pages=pages,
            engine="pymupdf_1.26.5_text_sort_false",
            transform_sha256=VERSION,
        ),
    )
    return pages


def build_links():
    cal = calendar()
    existing = pd.read_parquet(baseline("normalized/retired_equity_links.parquet"))
    rows = []
    reviews = json.loads((EP / "configs/v4_identity_page_reviews.json").read_text())
    for r in reviews:
        doc = json.loads(
            baseline(f"documents/retirement/{r['art_code']}.json").read_text()
        )
        if sha(source_bytes(doc["source"])) != r["source_sha256"]:
            raise ValueError("changed pixel-reviewed original")
        if doc["source"]["sha256"] != r["source_sha256"]:
            raise ValueError("reviewed original provenance mismatch")
        for image in r["images"]:
            for path, digest in [
                (image["full_image"], image["full_image_sha256"]),
                (image["code_crop"], image["code_crop_sha256"]),
            ]:
                if sha(V4 / path) != digest:
                    raise ValueError("changed reviewed image")
        date = doc["announcement"]["notice_date"][:10]
        rows.append(
            dict(
                **{
                    k: v
                    for k, v in r.items()
                    if k not in ["images", "contact_sheet", "contact_sha256"]
                },
                notice_date=date,
                known_at=str(cal.publication_time(date)),
                source_uri=doc["source"]["url"],
                index_sha256=doc["announcement"]["index_sha256"],
                legal_equity_continuity_evidence=True,
                actual_transfer_or_sale_proven=False,
                transform_sha256=VERSION,
            )
        )
    result = pd.concat([existing, pd.DataFrame(rows)], ignore_index=True)
    # Dates absent in typed v3 rows are computed from their original publication.
    result["known_at"] = result.notice_date.map(lambda x: str(cal.publication_time(x)))
    if (
        result.groupby("retired_code").security_id.nunique().max() != 1
        or result.groupby("security_id").retired_code.nunique().max() != 1
    ):
        raise ValueError("ambiguous retired issuer mapping")
    result.to_parquet(V4 / "normalized/retired_equity_links.parquet", index=False)
    result.to_csv(PUBLIC / "retired_equity_links.csv", index=False)
    return result


def usable_time(published_at, identity_known_at):
    if pd.isna(published_at) or pd.isna(identity_known_at):
        return pd.NaT
    return max(stamp(published_at), stamp(identity_known_at))


def make_queues():
    (V4 / "normalized").mkdir(parents=True, exist_ok=True)
    links, cal = build_links(), calendar()
    by_code = {
        code: g.sort_values("known_at").iloc[0].to_dict()
        for code, g in links.groupby("retired_code")
    }
    prior = pd.read_parquet(baseline("normalized/financial_version_chains.parquet"))
    notices = [
        json.loads(s)
        for s in pd.read_parquet(
            baseline("indices/retirement_complete.parquet")
        ).announcement
    ]
    finance, continuation = [], []
    for a in notices:
        codes = set(c["stock_code"] for c in a.get("codes", [])) & set(by_code)
        ids = {by_code[c]["security_id"] for c in codes}
        if len(ids) != 1:
            continue
        link = min((by_code[c] for c in codes), key=lambda x: x["known_at"])
        common = dict(
            security_id=link["security_id"],
            art_code=a["art_code"],
            title=a["title"],
            notice_date=a["notice_date"][:10],
            index_sha256=a["index_sha256"],
            index_partition="retirement",
            identity_link_art_code=link["art_code"],
            identity_link_source_sha256=link["source_sha256"],
            identity_link_known_at=link["known_at"],
            retired_code=link["retired_code"],
            source_publication_known_at=str(
                cal.publication_time(a["notice_date"][:10])
            ),
            known_at=str(
                usable_time(
                    cal.publication_time(a["notice_date"][:10]), link["known_at"]
                )
            ),
        )
        kind = classify_report(a["title"])
        if kind:
            finance.append(dict(**common, **kind))
        title = re.sub(r"\s+", "", a["title"])
        if any(k in title for k in ["挂牌转让公告", "挂牌公告"]) and not any(
            k in title for k in ["异常", "风险", "拟", "进展"]
        ):
            continuation.append(
                dict(**common, evidence_kind="RETIRED_BOARD_LISTING_ARRANGEMENT")
            )
    f = pd.DataFrame(finance)
    cninfo = []
    for path in (V4 / "documents/financial").glob("CNINFO_*.json"):
        record = json.loads(path.read_text())
        cninfo.append(record["announcement"])
    merged = pd.concat(
        [prior, f, pd.DataFrame(cninfo)], ignore_index=True
    ).drop_duplicates(["security_id", "art_code"], keep="first")
    redirects_path = V4 / "normalized/security_id_redirects.parquet"
    if redirects_path.exists():
        redirects = pd.read_parquet(redirects_path)
        lookup = dict(
            zip(redirects.legacy_security_id, redirects.canonical_security_id)
        )
        merged["indexed_security_id_v3"] = merged.security_id
        merged["security_id"] = merged.security_id.map(lambda x: lookup.get(x, x))
    merged["logical_report_key"] = (
        merged.security_id + "/" + merged.report_period + "/" + merged.form
    )
    chains = []
    for key, g in merged.groupby("logical_report_key", sort=True):
        predecessor = []
        original = g[~g.is_revision]
        for day, same_day in g.sort_values(["notice_date", "art_code"]).groupby(
            "notice_date", sort=True
        ):
            for r in same_day.to_dict("records"):
                r.update(
                    prior_version_ids=json.dumps(predecessor),
                    same_day_order_ambiguous=len(same_day) > 1,
                    original_report_present=not original.empty,
                    first_original_notice_date=(
                        None if original.empty else original.notice_date.min()
                    ),
                    source_index_does_not_certify_numeric_fields=True,
                    version_chain_status=(
                        "INDEXED_ORIGINAL_AND_REVISIONS"
                        if not original.empty
                        else "ORIGINAL_FIRST_VERSION_MISSING"
                    ),
                )
                chains.append(r)
            predecessor.extend(same_day.art_code)
    result = pd.DataFrame(chains)
    result.to_parquet(V4 / "normalized/financial_version_chains.parquet", index=False)
    result.to_csv(PUBLIC / "financial_version_chains.csv", index=False)
    # Every linked retired-issuer annual original/revision in a fixed period range.
    annual = f[
        f.form.eq("full_report")
        & f.report_period.str.endswith("12-31")
        & f.report_period.between("2016-01-01", "2025-12-31")
    ]
    gaps = pd.read_csv(baseline("provenance/v2_selected_financial_recovery_bridge.csv"))
    gap_keys = set(
        zip(
            gaps.loc[~gaps.v3_original_pdf_recovered, "security_id"],
            gaps.loc[~gaps.v3_original_pdf_recovered, "report_year"].astype(str)
            + "-12-31",
        )
    )
    old_missing = prior[
        prior.form.eq("full_report")
        & pd.Series(
            [(r.security_id, r.report_period) in gap_keys for r in prior.itertuples()],
            index=prior.index,
        )
    ]
    queue = pd.concat([annual, old_missing], ignore_index=True).drop_duplicates(
        "art_code"
    )
    queue["prior_selected_missing_period"] = [
        (r.security_id, r.report_period) in gap_keys for r in queue.itertuples()
    ]
    queue = queue.sort_values(
        [
            "prior_selected_missing_period",
            "security_id",
            "report_period",
            "notice_date",
        ],
        ascending=[False, True, True, True],
    )
    queue.to_parquet(V4 / "financial_queue.parquet", index=False)
    queue.to_csv(PUBLIC / "financial_original_queue.csv", index=False)
    pd.DataFrame(continuation).drop_duplicates("art_code").to_parquet(
        V4 / "continuation_queue.parquet", index=False
    )
    write_json(
        PUBLIC / "chain_summary.json",
        dict(
            baseline_linked_securities=67,
            linked_securities=links.security_id.nunique(),
            newly_pixel_reviewed_identities=len(links)
            - len(pd.read_parquet(baseline("normalized/retired_equity_links.parquet"))),
            retired_financial_disclosures=len(f),
            merged_financial_disclosures=len(result),
            new_financial_disclosures=len(result) - len(prior),
            additional_cninfo_version_records=len(cninfo),
            logical_report_chains=result.logical_report_key.nunique(),
            annual_original_queue=len(queue),
            continuation_notice_queue=len(continuation),
            source_publication_does_not_backdate_identity_link=True,
            transform_sha256=VERSION,
        ),
    )


def acquire():
    http = Capture()
    for group in ["financial", "continuation"]:
        queue = pd.read_parquet(V4 / f"{group}_queue.parquet")
        statuses = []
        for i, a in enumerate(queue.to_dict("records")):
            art = a["art_code"]
            target = V4 / f"documents/{group}/{art}.json"
            if target.exists():
                statuses.append(json.loads(target.read_text())["status"])
                continue
            # Reuse only verified originals already acquired in v3, across groups.
            reused = None
            for old in [
                f"documents/financial/{art}.json",
                f"documents/retirement/{art}.json",
            ]:
                try:
                    record = json.loads(baseline(old).read_text())
                except ValueError as exc:
                    if "undeclared baseline input" in str(exc):
                        continue
                    raise
                if record["status"] == "ORIGINAL_PDF_RECOVERED":
                    reused = record["source"]
                    source_bytes(reused)
                    break
            r = dict(
                announcement={k: (None if pd.isna(v) else v) for k, v in a.items()},
                status="UNKNOWN",
            )
            try:
                if reused is not None:
                    r.update(
                        status="ORIGINAL_PDF_RECOVERED",
                        source=reused,
                        source_reused_from_v3=True,
                    )
                else:
                    body, receipt = http.fetch(
                        group + "_" + art, f"https://pdf.dfcfw.com/pdf/H2_{art}_1.pdf"
                    )
                    if not body.startswith(b"%PDF"):
                        raise ValueError("not original PDF")
                    r.update(
                        status="ORIGINAL_PDF_RECOVERED",
                        source=receipt,
                        source_reused_from_v3=False,
                    )
            except PermissionError:
                raise
            except Exception as exc:
                r["error"] = str(exc)[:250]
            write_json(target, r)
            statuses.append(r["status"])
            if i % 25 == 0:
                print(group, i + 1, "/", len(queue), r["status"], flush=True)
            write_json(
                PUBLIC / f"{group}_acquisition.json",
                dict(
                    selected=len(queue),
                    processed=len(statuses),
                    recovered=statuses.count("ORIGINAL_PDF_RECOVERED"),
                    unresolved=statuses.count("UNKNOWN"),
                ),
            )


def parse():
    links = pd.read_parquet(V4 / "normalized/retired_equity_links.parquet")
    inv = pd.read_parquet(baseline("normalized/securities.parquet"))
    codes = {}
    for r in inv.itertuples():
        codes.setdefault(r.instrument[2:], set()).add(r.security_id)
    for r in pd.read_parquet(
        baseline("baseline/normalized/code_intervals.parquet")
    ).itertuples():
        codes.setdefault(r.historical_instrument[2:], set()).add(r.security_id)
    for r in links.itertuples():
        codes.setdefault(r.retired_code, set()).add(r.security_id)
    redirects_path = V4 / "normalized/security_id_redirects.parquet"
    if redirects_path.exists():
        redirects = pd.read_parquet(redirects_path)
        lookup = dict(
            zip(redirects.legacy_security_id, redirects.canonical_security_id)
        )
        codes = {
            code: {lookup.get(sid, sid) for sid in ids} for code, ids in codes.items()
        }
    values, docs, clauses = [], [], []
    for group in ["financial", "continuation"]:
        for path in sorted((V4 / f"documents/{group}").glob("*.json")):
            r = json.loads(path.read_text())
            a = r["announcement"]
            if r["status"] != "ORIGINAL_PDF_RECOVERED":
                continue
            if group == "financial":
                kind = classify_report(a["title"])
                if not kind or kind["form"] != "full_report":
                    continue
            pages = original_pages(r["source"])
            if group == "continuation":
                for i, page in enumerate(pages):
                    text = re.sub(r"\s+", "", page)
                    for m in re.finditer(
                        r"[^。]{0,100}(?:挂牌转让|办理股份确权|已确权|尚未确权)[^。]{0,180}[。]?",
                        text,
                    ):
                        clauses.append(
                            dict(
                                security_id=a["security_id"],
                                art_code=path.stem,
                                physical_page=i + 1,
                                exact_clause=m[0],
                                source_sha256=r["source"]["sha256"],
                                source_uri=r["source"]["url"],
                                notice_date=a["notice_date"],
                                known_at=a["known_at"],
                                evidence_status="ORIGINAL_ARRANGEMENT_REQUIRES_EVENT_REVIEW",
                                account_delivery_confirmed=False,
                                first_actual_trade_confirmed=False,
                                terminal_wealth=None,
                            )
                        )
                continue
            printed = set()
            for page in pages[:2]:
                for code in re.findall(
                    r"(?:(?:证券|股票|公司)代码|NEEQ)[:：为]?(\d{6})",
                    re.sub(r"\s+", "", page),
                ):
                    printed.update(codes.get(code, set()))
            candidates = []
            if printed == {a["security_id"]}:
                for i, page in enumerate(pages):
                    for value in parse_page(
                        page,
                        int(a["report_period"][:4]),
                        original_cover_year=cover_report_year(pages),
                    ):
                        candidates.append(dict(**value, physical_page=i + 1))
            counts = pd.Series(
                [x["field"] for x in candidates], dtype=str
            ).value_counts()
            candidates = [x for x in candidates if counts[x["field"]] == 1]
            for c in candidates:
                values.append(
                    dict(
                        **c,
                        security_id=a["security_id"],
                        art_code=path.stem,
                        report_period=a["report_period"],
                        notice_date=a["notice_date"],
                        candidate_known_at=a["known_at"],
                        is_revision=a["is_revision"],
                        source_sha256=r["source"]["sha256"],
                        source_uri=r["source"]["url"],
                        quality_tier="UNKNOWN/BLOCKED",
                        transform_sha256=VERSION,
                    )
                )
            docs.append(
                dict(
                    art_code=path.stem,
                    printed_identity_matched=printed == {a["security_id"]},
                    candidate_values=len(candidates),
                    source_sha256=r["source"]["sha256"],
                )
            )
    pd.DataFrame(values).to_parquet(
        V4 / "normalized/financial_value_candidates.parquet", index=False
    )
    pd.DataFrame(values).to_csv(PUBLIC / "financial_value_candidates.csv", index=False)
    pd.DataFrame(docs).to_csv(PUBLIC / "financial_source_parsing.csv", index=False)
    pd.DataFrame(clauses).to_parquet(
        V4 / "normalized/continuation_arrangement_clauses.parquet", index=False
    )
    pd.DataFrame(clauses).to_csv(
        PUBLIC / "continuation_arrangement_clauses.csv", index=False
    )
    write_json(
        PUBLIC / "parsing_summary.json",
        dict(
            financial_originals_parsed=len(docs),
            unreviewed_values=len(values),
            continuation_arrangement_clauses=len(clauses),
            numeric_candidates_promoted=0,
            transform_sha256=VERSION,
        ),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=["queues", "acquire", "parse"])
    args = p.parse_args()
    {"queues": make_queues, "acquire": acquire, "parse": parse}[args.phase]()
