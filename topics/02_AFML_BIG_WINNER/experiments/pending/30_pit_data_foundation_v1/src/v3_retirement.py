"""Post-delisting equity originals, indexed separately from A-share notices.

Current 400xxx securities are a discovery cohort, never the historical population.
An original explicitly linking the old A code to the retired code is required.
"""

import json
import pandas as pd
from archive import write_json, append_receipt
from v3_core import V3, PUBLIC3, Capture, save, read_verified, code_version
from v3_announcements import acquire_index, clean


def current_codes(http):
    rows, totals = [], []
    for page in range(1, 10):
        p = V3 / f"acquired/retired_current_list/page_{page:03d}.parquet"
        if p.exists():
            frame, rec = read_verified(p)
        else:
            params = dict(
                fltt=1,
                invt=2,
                np=1,
                pn=page,
                pz=500,
                fid="f12",
                po=1,
                fs="m:0+s:3",
                fields="f12,f13,f14,f26",
            )
            probe = V3 / "probes/retired_current_quote_list.json"
            if page == 1 and probe.exists():
                prior = json.loads(probe.read_text())
                rec = prior["source"]
                x = prior["payload"]["data"]
            else:
                b, rec = http.fetch(
                    "retired_current_discovery_list",
                    "https://push2.eastmoney.com/api/qt/clist/get",
                    params=params,
                )
                x = json.loads(b)["data"]
            frame = pd.DataFrame(x["diff"])
            frame["f26"] = frame.f26.astype(str)
            rec["reported_total"] = int(x["total"])
            save(frame, p, rec)
        rows.extend(frame.to_dict("records"))
        totals.append(rec["reported_total"])
        if len(rows) >= totals[0]:
            break
    f = pd.DataFrame(rows)
    if len(set(totals)) != 1 or len(f) != totals[0] or f.f12.duplicated().any():
        raise ValueError("retired discovery list pagination incomplete or unstable")
    f.to_csv(PUBLIC3 / "retirement_current_discovery_list.csv", index=False)
    return f[f.f12.str.fullmatch(r"400\d{3}")]


def select_originals(announcements):
    selected = []
    for a in announcements:
        title = clean(a["title"])
        if any(
            x in title
            for x in [
                "股份确权",
                "股票确权",
                "挂牌转让公告",
                "挂牌公告",
                "股票转让方式变更",
                "分类转让方式变更",
            ]
        ):
            if not any(
                x in title for x in ["异常", "风险提示", "进展", "可能", "关于拟"]
            ):
                selected.append(a)
    return selected


def main():
    PUBLIC3.mkdir(parents=True, exist_ok=True)
    version = code_version(__file__)
    http = Capture()
    # The current quote list became transport-inaccessible after its first page.
    # Enumerate the entire syntactic A-share retired-code namespace instead. Empty
    # codes contribute no facts; the issuer/date checks still apply to every row.
    # This also finds companies absent from today's surviving retired-code list.
    discovery = pd.DataFrame(dict(f12=[f"400{i:03d}" for i in range(1000)]))
    cohort = pd.DataFrame(dict(instrument="RT" + discovery.f12))
    announcements = acquire_index(http, "retirement", cohort, 0, 0, ann_type="SB")
    selected = select_originals(announcements)
    pd.DataFrame(
        [
            dict(art_code=a["art_code"], title=a["title"], notice_date=a["notice_date"])
            for a in selected
        ]
    ).to_csv(PUBLIC3 / "retirement_original_queue.csv", index=False)
    statuses = []
    # Identity confirmations precede subsequent classification changes.
    selected.sort(
        key=lambda a: (
            not any(x in clean(a["title"]) for x in ["股份确权", "股票确权"]),
            a["notice_date"],
            a["art_code"],
        )
    )
    for i, a in enumerate(selected):
        p = V3 / f"documents/retirement/{a['art_code']}.json"
        if p.exists():
            statuses.append(json.loads(p.read_text())["status"])
            continue
        r = dict(
            announcement=a,
            status="UNKNOWN",
            evidence_kind="POST_DELISTING_EQUITY_ORIGINAL",
        )
        try:
            b, rec = http.fetch(
                "retirement_original_" + a["art_code"],
                "https://pdf.dfcfw.com/pdf/H2_" + a["art_code"] + "_1.pdf",
            )
            if not b.startswith(b"%PDF"):
                raise ValueError("not an original PDF")
            r.update(status="ORIGINAL_PDF_RECOVERED", source=rec)
        except PermissionError:
            raise
        except Exception as exc:
            r["error"] = str(exc)[:250]
        write_json(p, r)
        statuses.append(r["status"])
        append_receipt(
            PUBLIC3 / "retirement_original_progress.jsonl",
            dict(art_code=a["art_code"], status=r["status"]),
        )
        if i % 50 == 0:
            print("retirement originals", i + 1, "/", len(selected), flush=True)
    write_json(
        PUBLIC3 / "retirement_acquisition_summary.json",
        dict(
            syntactic_retired_code_candidates=len(discovery),
            complete_announcements=len(announcements),
            selected_originals=len(selected),
            recovered=statuses.count("ORIGINAL_PDF_RECOVERED"),
            transform_sha256=version,
            historical_population_certified=False,
            discovery="entire 400000-400999 namespace, not today's survivor list",
            all_historical_retired_issuers_certified=False,
        ),
    )


if __name__ == "__main__":
    main()
