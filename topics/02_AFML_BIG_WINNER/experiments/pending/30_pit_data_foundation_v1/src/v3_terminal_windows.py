"""Cross-category final delisting notices around each candidate exit boundary.

Category-only risk indices miss final notices classified as major events. Query
the full category set in bounded issuer/date windows, retaining every result.
"""

import json
import pandas as pd
from archive import EP, write_json
from v3_core import V3, PUBLIC3, Capture, inventory, save, read_verified, code_version


def main():
    version = code_version(__file__)
    inv = inventory()
    early = pd.read_csv(EP / "outputs/backfill_v2/legacy_early_history_end_audit.csv")
    targets = inv[
        inv.delist_date.ge("2017-01-03") | inv.instrument.isin(early.instrument)
    ].copy()
    http = Capture()
    allrows, audit = [], []
    for i, row in enumerate(targets.itertuples()):
        end = row.delist_date
        if pd.isna(end):
            from v3_core import V2_RELEASE

            bars = pd.read_parquet(
                V2_RELEASE / f"normalized/prices/{row.security_id}.parquet"
            )
            end = bars.date.max()
        start = max(
            pd.Timestamp(end) - pd.Timedelta(days=120), pd.Timestamp("2016-01-01")
        )
        stop = min(
            pd.Timestamp(end) + pd.Timedelta(days=120), pd.Timestamp("2026-10-21")
        )
        records, totals, page = [], [], 1
        while True:
            p = (
                V3
                / f"indices/terminal_windows/{row.instrument}/page_{page:03d}.parquet"
            )
            if p.exists():
                f, rec = read_verified(p)
            else:
                params = dict(
                    sr=1,
                    page_size=100,
                    page_index=page,
                    ann_type="A",
                    client_source="web",
                    begin_time=str(start.date()),
                    end_time=str(stop.date()),
                    stock_list=row.instrument[2:],
                    f_node=0,
                    s_node=0,
                )
                b, rec = http.fetch(
                    "terminal_window_" + row.instrument,
                    "https://np-anotice-stock.eastmoney.com/api/security/ann",
                    params=params,
                )
                x = json.loads(b)
                if x.get("success") != 1:
                    raise ValueError("terminal index unsuccessful")
                data = x["data"]
                f = pd.DataFrame(
                    [
                        dict(
                            art_code=a["art_code"],
                            announcement=json.dumps(a, ensure_ascii=False),
                        )
                        for a in data["list"]
                    ],
                    columns=["art_code", "announcement"],
                )
                rec.update(
                    reported_total=int(data["total_hits"]), transform_sha256=version
                )
                save(f, p, rec)
            totals.append(rec["reported_total"])
            for text in f.announcement:
                a = json.loads(text)
                if row.instrument[2:] not in {
                    c["stock_code"] for c in a.get("codes", [])
                }:
                    raise ValueError("terminal issuer filter ignored")
                if not str(start.date()) <= a["notice_date"][:10] <= str(stop.date()):
                    raise ValueError("terminal date filter ignored")
                a.update(
                    index_sha256=rec["sha256"],
                    index_partition="terminal_windows",
                    instrument=row.instrument,
                    security_id=row.security_id,
                )
                records.append(a)
            if len(records) >= totals[0]:
                break
            if f.empty:
                raise ValueError("terminal window has missing page")
            page += 1
        if (
            len(set(totals)) != 1
            or len(records) != totals[0]
            or len({a["art_code"] for a in records}) != len(records)
        ):
            raise ValueError("incomplete or unstable terminal window index")
        allrows.extend(records)
        audit.append(
            dict(
                instrument=row.instrument,
                security_id=row.security_id,
                begin=str(start.date()),
                end=str(stop.date()),
                reported_count=totals[0],
                acquired_count=len(records),
                complete=True,
            )
        )
        if i % 25 == 0:
            print("exit windows", i + 1, "/", len(targets), flush=True)
    pd.DataFrame(
        [
            dict(art_code=a["art_code"], announcement=json.dumps(a, ensure_ascii=False))
            for a in allrows
        ]
    ).to_parquet(V3 / "indices/terminal_windows_complete.parquet", index=False)
    pd.DataFrame(audit).to_csv(
        PUBLIC3 / "terminal_window_completeness.csv", index=False
    )
    selected = {}
    latest_risk = {}
    for a in allrows:
        if any(k in a["title"] for k in ["终止上市", "摘牌", "退市整理期", "股份确权"]):
            if not any(
                k in a["title"] for k in ["可能", "申请", "法律意见", "核查", "问询"]
            ):
                if "风险提示" in a["title"] or "提示性" in a["title"]:
                    old = latest_risk.get(a["security_id"])
                    if old is None or a["notice_date"] > old["notice_date"]:
                        latest_risk[a["security_id"]] = a
                else:
                    selected[a["art_code"]] = a
    selected.update({a["art_code"]: a for a in latest_risk.values()})
    done = []
    for i, a in enumerate(
        sorted(
            selected.values(),
            key=lambda a: ("摘牌" not in a["title"], a["notice_date"], a["art_code"]),
        )
    ):
        p = V3 / f"documents/core/{a['art_code']}.json"
        if p.exists():
            done.append(json.loads(p.read_text())["status"])
            continue
        r = dict(
            announcement=a,
            evidence_kind="TERMINAL_OR_RELISTING",
            status="UNKNOWN",
            supplemental_exit_window=True,
        )
        try:
            b, rec = http.fetch(
                "terminal_window_original_" + a["art_code"],
                "https://pdf.dfcfw.com/pdf/H2_" + a["art_code"] + "_1.pdf",
            )
            if not b.startswith(b"%PDF"):
                raise ValueError("not PDF")
            r.update(status="ORIGINAL_PDF_RECOVERED", source=rec)
        except PermissionError:
            raise
        except Exception as exc:
            r["error"] = str(exc)[:250]
        write_json(p, r)
        done.append(r["status"])
        if i % 50 == 0:
            print("exit window originals", i + 1, "/", len(selected), flush=True)
    write_json(
        PUBLIC3 / "terminal_window_summary.json",
        dict(
            issuers=len(targets),
            indexed_announcements=len(allrows),
            selected_originals=len(selected),
            recovered=done.count("ORIGINAL_PDF_RECOVERED"),
            transform_sha256=version,
        ),
    )


if __name__ == "__main__":
    main()
