"""Complete validated issuer-cohort announcement indices, then original evidence PDFs.

Endpoint f_node/s_node use UI numeric node ids, NOT returned column_code strings.
Every result is checked against requested issuers and dates before completeness.
"""

import argparse
import json
import re
import math
import pandas as pd
from archive import EP, write_json, append_receipt
from v3_core import V3, PUBLIC3, Capture, save, read_verified, inventory, code_version


def clean(text):
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", str(text)))


def core_cohort():
    inv = inventory()
    old = pd.read_csv(EP / "outputs/backfill_v2/legacy_early_history_end_audit.csv")
    selected = inv[
        inv.delist_date.ge("2017-01-03")
        | inv.identity_date_conflict
        | inv.instrument.isin(old.instrument)
    ]
    fixed = [
        "SH600000",
        "SH600019",
        "SZ000001",
        "SZ000066",
        "SZ000584",
        "SH688001",
        "BJ920001",
    ]
    return inv[
        inv.security_id.isin(selected.security_id) | inv.instrument.isin(fixed)
    ].copy()


def financial_cohort():
    inv = inventory()
    return inv[
        inv.exchange.eq("BJ")
        | inv.delist_date.ge("2017-01-03")
        | inv.instrument.isin(core_cohort().instrument)
    ]


def kind_of(title):
    t = clean(title)
    if any(
        x in t
        for x in [
            "可能",
            "风险提示",
            "进展",
            "进度",
            "风险的",
            "风险公告",
            "问询",
            "核查意见",
            "法律意见",
            "财务顾问",
            "交易异常",
            "投资者",
            "交易严重",
            "承诺",
            "申请撤销",
            "申请摘除",
            "停牌期间",
        ]
    ):
        # Final termination notices can mention future risk only in body, not title.
        if "风险警示" not in t or any(x in t for x in ["申请", "可能", "提示", "进展"]):
            return None
    if "实施" in t and any(x in t for x in ["权益分派", "分红派息", "利润分配"]):
        if not any(
            x in t
            for x in [
                "停止转股",
                "暂停转股",
                "转债",
                "B股",
                "H股",
                "股东大会",
                "董事会",
            ]
        ):
            return "DISTRIBUTION_IMPLEMENTATION"
    if any(x in t for x in ["现金选择权", "换股实施", "新增股份上市", "合并实施结果"]):
        return "MERGER_OR_CASH_OPTION"
    if any(
        x in t
        for x in [
            "终止上市",
            "摘牌",
            "退市整理期",
            "退市板块",
            "股份确权",
            "恢复上市",
            "重新上市",
            "重新挂牌",
            "挂牌转让",
        ]
    ):
        if not any(
            x in t
            for x in [
                "可能",
                "风险提示",
                "风险公告",
                "上市风险",
                "进展",
                "律师",
                "财务顾问",
                "申请书",
                "方案",
                "申请股票",
            ]
        ):
            return "TERMINAL_OR_RELISTING"
    if "风险警示" in t and any(x in t for x in ["实施", "撤销", "变更", "变为"]):
        if not any(
            x in t for x in ["可能", "提示", "申请", "进展", "股东大会", "董事会"]
        ):
            return "RISK_WARNING_CHANGE"
    if any(
        x in t
        for x in [
            "停牌",
            "复牌",
            "证券简称变更",
            "变更证券简称",
            "股票简称变更",
            "变更股票简称",
        ]
    ):
        if not any(
            x in t
            for x in [
                "转债",
                "可转债",
                "公司债",
                "停牌期间",
                "停牌进展",
                "问询",
                "换股价格",
            ]
        ):
            return "SUSPENSION_RESUMPTION_OR_NAME"
    return None


def acquire_index(http, label, cohort, f_node, s_node=0, ann_type="A"):
    version = code_version(__file__)
    records = []
    audit = []
    # Small issuer batches keep results below the endpoint's 50,000 cap.
    codes = sorted(set(cohort.instrument.str[2:]))
    for i in range(0, len(codes), 40):
        batch = codes[i : i + 40]
        batch_id = i // 40
        page = 1
        total = None
        complete = []
        seen = set()
        while True:
            path = V3 / f"indices/{label}/batch_{batch_id:03d}/page_{page:04d}.parquet"
            if path.exists():
                frame, rec = read_verified(path)
                data = frame.to_dict("records")
                n = rec["reported_total"]
            else:
                params = dict(
                    sr=1,
                    page_size=100,
                    page_index=page,
                    ann_type=ann_type,
                    client_source="web",
                    begin_time="2016-01-01",
                    end_time="2026-10-21",
                    f_node=f_node,
                    s_node=s_node,
                    stock_list=",".join(batch),
                )
                body, rec = http.fetch(
                    "index_" + label,
                    "https://np-anotice-stock.eastmoney.com/api/security/ann",
                    params=params,
                )
                payload = json.loads(body)
                if payload.get("success") != 1:
                    raise ValueError("issuer index unsuccessful")
                result = payload.get("data") or {}
                n = int(result.get("total_hits") or 0)
                data = result.get("list") or []
                if n >= 50000:
                    raise ValueError(
                        "endpoint cap reached; split issuer/date partition"
                    )
                # JSON strings preserve nested metadata without dtype surprises on reload.
                frame = pd.DataFrame(
                    [
                        dict(
                            art_code=a["art_code"],
                            announcement=json.dumps(a, ensure_ascii=False),
                        )
                        for a in data
                    ],
                    columns=["art_code", "announcement"],
                )
                rec.update(
                    reported_total=n,
                    issuers=batch,
                    node=[f_node, s_node],
                    transform_sha256=version,
                )
                save(frame, path, rec)
                data = frame.to_dict("records")
            if total is None:
                total = n
            if n != total:
                raise ValueError(
                    "announcement count drift; complete historical index not attested"
                )
            if not data and len(complete) < total:
                raise ValueError("missing announcement page")
            for row in data:
                a = json.loads(row["announcement"])
                if not set(c["stock_code"] for c in a.get("codes", [])).intersection(
                    batch
                ):
                    raise ValueError("issuer filter ignored")
                if not "2016-01-01" <= a["notice_date"][:10] <= "2026-10-21":
                    raise ValueError("date filter ignored")
                if a["art_code"] in seen:
                    raise ValueError("duplicate across pages, snapshot unstable")
                seen.add(a["art_code"])
                a.update(
                    index_sha256=rec["sha256"],
                    index_partition=label,
                    index_batch=batch_id,
                )
                complete.append(a)
            if len(complete) == total:
                break
            if len(complete) > total:
                raise ValueError("announcement count exceeded")
            page += 1
        records.extend(complete)
        audit.append(
            dict(
                partition=label,
                batch=batch_id,
                reported_count=total,
                acquired_count=len(complete),
                pages=page,
                complete=True,
            )
        )
        print(
            "index",
            label,
            batch_id + 1,
            "/",
            math.ceil(len(codes) / 40),
            "rows",
            len(complete),
            flush=True,
        )
    out = V3 / f"indices/{label}_complete.parquet"
    pd.DataFrame(
        [
            dict(art_code=a["art_code"], announcement=json.dumps(a, ensure_ascii=False))
            for a in records
        ]
    ).drop_duplicates("art_code").to_parquet(out, index=False)
    pd.DataFrame(audit).to_csv(PUBLIC3 / f"index_{label}_completeness.csv", index=False)
    return records


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["core", "financial"], default="core")
    p.add_argument("--index-only", action="store_true")
    args = p.parse_args()
    http = Capture()
    PUBLIC3.mkdir(parents=True, exist_ok=True)
    if args.phase == "financial":
        cohort = financial_cohort()
        groups = [("financial", 1, 1)]
    else:
        cohort = core_cohort()
        groups = [
            ("risk", 3, 0),
            ("distributions", 1, 13),
            ("identity", 4, 0),
            ("mergers", 6, 11),
        ]
    cohort.to_csv(PUBLIC3 / (args.phase + "_cohort.csv"), index=False)
    allrows = []
    for label, node, subnode in groups:
        allrows.extend(acquire_index(http, label, cohort, node, subnode))
    unique = {a["art_code"]: a for a in allrows}
    candidates = []
    for a in unique.values():
        kind = kind_of(a["title"])
        if args.phase == "core" and kind:
            candidates.append(dict(**a, evidence_kind=kind))
    if args.phase == "core":
        pd.DataFrame(
            [
                dict(
                    art_code=a["art_code"],
                    title=a["title"],
                    notice_date=a["notice_date"],
                    evidence_kind=a["evidence_kind"],
                )
                for a in candidates
            ]
        ).to_csv(PUBLIC3 / "core_original_document_queue.csv", index=False)
    write_json(
        PUBLIC3 / (args.phase + "_index_summary.json"),
        dict(
            issuers=len(cohort),
            unique_announcements=len(unique),
            selected_original_documents=len(candidates),
            all_partition_counts_complete=True,
        ),
    )
    if args.index_only or args.phase == "financial":
        return
    priority = {
        "TERMINAL_OR_RELISTING": 0,
        "MERGER_OR_CASH_OPTION": 1,
        "DISTRIBUTION_IMPLEMENTATION": 2,
        "RISK_WARNING_CHANGE": 3,
        "SUSPENSION_RESUMPTION_OR_NAME": 4,
    }
    candidates.sort(
        key=lambda a: (priority[a["evidence_kind"]], a["notice_date"], a["art_code"])
    )
    done = []
    for i, a in enumerate(candidates):
        result = V3 / f"documents/core/{a['art_code']}.json"
        if result.exists():
            done.append(json.loads(result.read_text()))
            continue
        r = dict(announcement=a, status="UNKNOWN", evidence_kind=a["evidence_kind"])
        try:
            url = "https://pdf.dfcfw.com/pdf/H2_" + a["art_code"] + "_1.pdf"
            body, rec = http.fetch("issuer_original_" + a["art_code"], url)
            if not body.startswith(b"%PDF"):
                raise ValueError("source is not PDF")
            r.update(status="ORIGINAL_PDF_RECOVERED", source=rec)
        except PermissionError:
            raise
        except Exception as exc:
            r["error"] = str(exc)[:250]
        write_json(result, r)
        done.append(r)
        append_receipt(
            PUBLIC3 / "core_document_progress.jsonl",
            dict(
                art_code=a["art_code"],
                status=r["status"],
                evidence_kind=a["evidence_kind"],
            ),
        )
        if i % 100 == 0:
            print(
                "originals", i + 1, "/", len(candidates), a["evidence_kind"], flush=True
            )
    write_json(
        PUBLIC3 / "core_document_summary.json",
        dict(
            selected=len(candidates),
            recovered=sum(r["status"] == "ORIGINAL_PDF_RECOVERED" for r in done),
            unresolved=sum(r["status"] != "ORIGINAL_PDF_RECOVERED" for r in done),
        ),
    )


if __name__ == "__main__":
    main()
