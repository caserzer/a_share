"""Retrieve complete reported public share/action tables with preserved pagination.

Retrospective vendor tables stay proxy. Date fields never certify first versions.
"""

import argparse
import json
from pathlib import Path
import pandas as pd
from archive import sha, write_json
from backfill_rpc import V2, PUBLIC
from backfill_http import CapturedHTTP, write_partition

SPECS = {
    "shares": dict(
        url="https://datacenter.eastmoney.com/securities/api/data/v1/get",
        reportName="RPT_F10_EH_EQUITY",
        columns="SECUCODE,SECURITY_CODE,END_DATE,TOTAL_SHARES,LISTED_A_SHARES,FREE_SHARES,CHANGE_REASON",
        filter="(END_DATE<='2026-10-21')",
        sortColumns="END_DATE,SECUCODE,CHANGE_REASON",
        sortTypes="1,1,1",
    ),
    "corporate_actions": dict(
        url="https://datacenter-web.eastmoney.com/api/data/v1/get",
        reportName="RPT_SHAREBONUS_DET",
        columns="ALL",
        filter="(NOTICE_DATE<='2026-10-21')",
        sortColumns="NOTICE_DATE,SECURITY_CODE,REPORT_DATE",
        sortTypes="1,1,1",
    ),
    "rights_issues": dict(
        url="https://datacenter-web.eastmoney.com/api/data/v1/get",
        reportName="RPT_IPO_ALLOTMENT",
        columns="ALL",
        filter="",
        sortColumns="EQUITY_RECORD_DATE,SECURITY_CODE",
        sortTypes="1,1",
    ),
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("domains", nargs="*", default=list(SPECS))
    args = p.parse_args()
    http = CapturedHTTP()
    for domain in args.domains:
        spec = SPECS[domain].copy()
        url = spec.pop("url")
        spec.update(pageSize="5000", pageNumber="1", source="HSF10", client="PC")
        page = 1
        pages = 1
        expected = None
        frames = []
        source_hashes = []
        while page <= pages:
            path = V2 / f"acquired/tables/{domain}/page_{page:04d}.parquet"
            rp = Path(str(path) + ".receipt.json")
            if path.exists() and rp.exists():
                rec = json.loads(rp.read_text())
                if sha(path) != rec["parquet_sha256"]:
                    raise ValueError("cached table page changed")
                f = pd.read_parquet(path)
                n = rec["reported_count"]
                pages = rec["reported_pages"]
            else:
                params = {**spec, "pageNumber": str(page)}
                body, rec = http.fetch("eastmoney_" + domain, url, params=params)
                payload = json.loads(body)
                result = payload.get("result") or {}
                data = result.get("data") or []
                if not data:
                    raise ValueError(
                        f"{domain} missing page {page}: " + str(payload.get("message"))
                    )
                pages = int(result.get("pages") or 1)
                n = int(result.get("count") or len(data))
                f = pd.DataFrame(data)
                rec.update(
                    reported_count=n,
                    reported_pages=pages,
                    transform_sha256=sha(__file__),
                )
                rec = write_partition(f, path, rec)
            if expected is None:
                expected = n
            if n != expected:
                raise ValueError(
                    f"{domain} row count changed during pagination: preserve both, do not certify complete"
                )
            frames.append(f)
            source_hashes.append(rec["sha256"])
            print(domain, "page", page, "/", pages, "rows", len(f), flush=True)
            page += 1
        allrows = pd.concat(frames, ignore_index=True)
        if len(allrows) != expected:
            raise ValueError(
                f"{domain} pagination row count mismatch {len(allrows)}/{expected}"
            )
        folder = V2 / "tables"
        folder.mkdir(exist_ok=True)
        out = folder / (domain + ".parquet")
        allrows.to_parquet(out, index=False)
        summary = dict(
            domain=domain,
            rows=len(allrows),
            reported_rows=expected,
            pages=pages,
            exact_duplicate_rows=int(allrows.astype(str).duplicated().sum()),
            columns=list(allrows),
            source_response_sha256=source_hashes,
            parquet_path=str(out),
            parquet_sha256=sha(out),
            first_version_certified=False,
            quality_tier="Historical-proxy",
            raw_pages_complete=True,
            atomic_vendor_snapshot_certified=False,
        )
        write_json(PUBLIC / (domain + "_table_summary.json"), summary)
        print(domain, "complete", len(allrows), flush=True)


if __name__ == "__main__":
    main()
