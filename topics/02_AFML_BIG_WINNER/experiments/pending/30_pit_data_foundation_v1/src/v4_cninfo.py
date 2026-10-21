"""Independent original-disclosure search for remaining selected annual periods.

Retrieve every page (actual page length may be 30 despite requested 100), validate
issuer/date/count, and keep all original/corrected full-report versions.
"""

import argparse
import json
import re
from pathlib import Path

import pandas as pd

from archive import archive_bytes, write_json
from v4_core import V4, PUBLIC, Capture, baseline
from v4_pipeline import calendar, classify_report

VERSION = archive_bytes(Path(__file__).read_bytes(), root=V4)[1]


def search(http, row, all_titles=False):
    namespace = "all_title_indices_page30" if all_titles else "indices_page30"
    namespace += "_verified_aliases"
    target = V4 / f"cninfo/{namespace}/{row['instrument']}_{row['report_year']}.json"
    if target.exists():
        return json.loads(target.read_text())
    code = row["instrument"][2:]
    allowed_codes, alias_links = {code}, {}
    aliases = V4 / "normalized/security_id_redirects.parquet"
    if aliases.exists():
        for alias in pd.read_parquet(aliases).to_dict("records"):
            if row["security_id"] == alias["canonical_security_id"]:
                allowed_codes.add(alias["new_instrument"][2:])
                alias_links[alias["new_instrument"][2:]] = alias
    org = row["org_id"]
    if pd.isna(org):
        org = ("gssz0" if row["instrument"].startswith("SZ") else "gssh0") + code
    rows, seen, sources, expected = [], set(), [], None
    for page in range(1, 101):
        payload = dict(
            pageNum=page,
            pageSize=30,
            tabName="fulltext",
            column="szse",
            stock=f"{code},{org}",
            searchkey="" if all_titles else "年度报告",
            seDate=f"{int(row['report_year'])+1}-01-01~2026-10-21",
            isHLtitle="true",
            sortName="time",
            sortType="asc",
        )
        body, receipt = http.fetch(
            "missing_period_cninfo_index",
            "https://www.cninfo.com.cn/new/hisAnnouncement/query",
            data=payload,
            method="POST",
        )
        result = json.loads(body)
        n = int(result.get("totalAnnouncement") or 0)
        if expected is None:
            expected = n
        if n != expected:
            raise ValueError("unstable CNINFO count")
        announcements = result.get("announcements") or []
        sources.append(receipt)
        if not announcements and len(rows) < n:
            raise ValueError("missing CNINFO page")
        for a in announcements:
            if a["secCode"] not in allowed_codes:
                raise ValueError("CNINFO issuer filter mismatch")
            pub = (
                pd.to_datetime(a["announcementTime"], unit="ms", utc=True)
                .tz_convert("Asia/Shanghai")
                .date()
                .isoformat()
            )
            if not f"{int(row['report_year'])+1}-01-01" <= pub <= "2026-10-21":
                raise ValueError("CNINFO date filter ignored")
            if a["announcementId"] in seen:
                raise ValueError("duplicate CNINFO pagination")
            seen.add(a["announcementId"])
            rows.append(
                dict(
                    **a,
                    verified_publication_date=pub,
                    index_sha256=receipt["sha256"],
                    identity_link_known_at=alias_links.get(a["secCode"], {}).get(
                        "known_at"
                    ),
                    identity_link_source_sha256=alias_links.get(a["secCode"], {}).get(
                        "source_sha256"
                    ),
                )
            )
        if len(rows) == n:
            r = dict(
                instrument=row["instrument"],
                security_id=row["security_id"],
                report_year=row["report_year"],
                reported_total=n,
                acquired_count=len(rows),
                complete=True,
                sources=sources,
                announcements=rows,
                transform_sha256=VERSION,
            )
            write_json(target, r)
            return r
        if len(rows) > n:
            raise ValueError("CNINFO count exceeded")
    raise ValueError("CNINFO page cap reached, no complete index attested")


def run(all_titles=False, only_instrument=None):
    inv = pd.read_parquet(baseline("normalized/securities.parquet"))
    gaps = pd.read_csv(baseline("provenance/v2_selected_financial_recovery_bridge.csv"))
    gaps = gaps[~gaps.v3_original_pdf_recovered]
    recovered = set()
    for p in (V4 / "documents/financial").glob("*.json"):
        r = json.loads(p.read_text())
        a = r["announcement"]
        kind = classify_report(a["title"])
        if (
            r["status"] == "ORIGINAL_PDF_RECOVERED"
            and kind
            and kind["form"] == "full_report"
        ):
            recovered.add((a["security_id"], a["report_period"]))
    queue = gaps[
        [
            (r.security_id, str(r.report_year) + "-12-31") not in recovered
            for r in gaps.itertuples()
        ]
    ].merge(inv[["security_id", "org_id"]], on="security_id", validate="many_to_one")
    if only_instrument:
        queue = queue[queue.instrument.eq(only_instrument)]
    prefix = (
        "cninfo_all_titles_page30" if all_titles else "cninfo_missing_period_page30"
    )
    prefix += "_verified_aliases"
    queue.to_csv(PUBLIC / (prefix + "_queue.csv"), index=False)
    cal, http = calendar(), Capture()
    audit = []
    for row in queue.sort_values("instrument").to_dict("records"):
        result_namespace = (
            "all_title_results_page30" if all_titles else "results_page30"
        )
        result_namespace += "_verified_aliases"
        result_path = (
            V4
            / f"cninfo/{result_namespace}/{row['instrument']}_{row['report_year']}.json"
        )
        if result_path.exists():
            audit.append(json.loads(result_path.read_text()))
            continue
        r = dict(
            instrument=row["instrument"],
            security_id=row["security_id"],
            report_year=row["report_year"],
            status="UNKNOWN",
            full_reports=0,
        )
        try:
            index = search(http, row, all_titles=all_titles)
            r.update(index_complete=True, index_rows=len(index["announcements"]))
            selected = []
            for a in index["announcements"]:
                title = re.sub(r"<[^>]*>", "", a["announcementTitle"])
                kind = classify_report(title)
                if (
                    kind
                    and kind["form"] == "full_report"
                    and kind["report_period"] == str(row["report_year"]) + "-12-31"
                ):
                    selected.append((a, title, kind))
            for a, title, kind in selected:
                art = "CNINFO_" + a["announcementId"]
                target = V4 / f"documents/financial/{art}.json"
                if target.exists():
                    saved = json.loads(target.read_text())
                    r["full_reports"] += int(
                        saved["status"] == "ORIGINAL_PDF_RECOVERED"
                    )
                    continue
                announcement = dict(
                    security_id=row["security_id"],
                    art_code=art,
                    title=title,
                    notice_date=a["verified_publication_date"],
                    known_at=str(
                        max(
                            cal.publication_time(a["verified_publication_date"]),
                            pd.Timestamp(a["identity_link_known_at"]),
                        )
                        if a.get("identity_link_known_at")
                        else cal.publication_time(a["verified_publication_date"])
                    ),
                    identity_link_known_at=a.get("identity_link_known_at"),
                    identity_link_source_sha256=a.get("identity_link_source_sha256"),
                    index_sha256=a["index_sha256"],
                    index_partition="cninfo_missing_selected_periods",
                    **kind,
                )
                record = dict(announcement=announcement, status="UNKNOWN")
                try:
                    adjunct = a["adjunctUrl"]
                    if not re.fullmatch(
                        r"finalpage/\d{4}-\d{2}-\d{2}/[A-Za-z0-9_.-]+\.PDF",
                        adjunct,
                        re.I,
                    ):
                        raise ValueError("unexpected declared CNINFO attachment path")
                    body, receipt = http.fetch(
                        "cninfo_original_" + art,
                        "https://static.cninfo.com.cn/" + adjunct,
                    )
                    if not body.startswith(b"%PDF"):
                        raise ValueError("CNINFO original not PDF")
                    record.update(
                        status="ORIGINAL_PDF_RECOVERED",
                        source=receipt,
                        source_reused_from_v3=False,
                    )
                    r["full_reports"] += 1
                except PermissionError:
                    raise
                except Exception as exc:
                    record["error"] = str(exc)[:250]
                write_json(target, record)
            r["status"] = (
                "ORIGINAL_PDF_RECOVERED"
                if r["full_reports"]
                else (
                    "NO_FULL_REPORT_IN_COMPLETE_VERIFIED_QUERY"
                    if not selected
                    else "ORIGINAL_ATTACHMENT_UNRESOLVED"
                )
            )
        except PermissionError:
            raise
        except Exception as exc:
            r["error"] = str(exc)[:250]
        write_json(result_path, r)
        audit.append(r)
        pd.DataFrame(audit).to_csv(PUBLIC / (prefix + "_results.csv"), index=False)
        print(
            row["instrument"],
            row["report_year"],
            r["status"],
            r["full_reports"],
            flush=True,
        )
    pd.DataFrame(audit).to_csv(PUBLIC / (prefix + "_results.csv"), index=False)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--all-titles", action="store_true")
    p.add_argument("--instrument")
    a = p.parse_args()
    run(all_titles=a.all_titles, only_instrument=a.instrument)
