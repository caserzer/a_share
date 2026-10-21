"""Bounded public-source discovery. Every success/failure remains in receipts.

No credentials, purchases or model work. Live lists are observations today,
never certified historical population. Offline audit reuses archived responses.
"""

from io import BytesIO
import argparse
import json
import time
import pandas as pd
import requests

from archive import EP, CACHE, archive_bytes, append_receipt, utc_now


def specs():
    common = {
        "sqlId": "COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L",
        "isPagination": "true",
        "type": "inParams",
        "pageHelp.pageSize": "10000",
        "pageHelp.pageNo": "1",
    }
    for name, typ, status in [
        ("sse_main", "1", "2,4,5,7,8"),
        ("sse_star", "8", "2,4,5,7,8"),
        ("sse_delisted", "1,8", "3"),
    ]:
        yield (
            name,
            "GET",
            "https://query.sse.com.cn/sseQuery/commonQuery.do",
            {**common, "STOCK_TYPE": typ, "COMPANY_STATUS": status},
        )
    for name, catalog, tab in [
        ("szse_active", "1110", "tab1"),
        ("szse_delisted", "1793_ssgs", "tab2"),
    ]:
        yield (
            name,
            "GET",
            "https://www.szse.cn/api/report/ShowReport",
            {"SHOWTYPE": "xlsx", "CATALOGID": catalog, "TABKEY": tab},
        )
    yield (
        "bse_page0",
        "POST",
        "https://www.bse.cn/nqxxController/nqxxCnzq.do",
        {
            "page": "0",
            "typejb": "T",
            "xxfcbj[]": "2",
            "sortfield": "xxzqdm",
            "sorttype": "asc",
        },
    )
    yield "cninfo_portal", "GET", "https://www.cninfo.com.cn/", {}
    yield (
        "szse_suspension_202603",
        "GET",
        "https://docs.static.szse.cn/www/market/periodical/month/W020260403534498695444.html",
        {},
    )
    yield (
        "financial_correction_example",
        "GET",
        "https://static.cninfo.com.cn/finalpage/2024-07-31/1220755915.PDF",
        {},
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    receipts = EP / "outputs/audits/source_attempts.jsonl"
    if not args.live:
        raise SystemExit("Use --live explicitly; archived data is read by run_audit.py")
    for name, method, url, params in specs():
        r = {
            "source_id": name,
            "url": url,
            "params": params,
            "method": method,
            "source_observed_at": utc_now(),
            "known_at": None,
            "historical_tier": "Historical-proxy",
        }
        try:
            kwargs = {"params" if method == "GET" else "data": params}
            response = requests.request(
                method,
                url,
                timeout=(8, 20),
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://www.sse.com.cn/",
                },
                **kwargs,
            )
            path, digest = archive_bytes(response.content)
            r.update(
                http_status=response.status_code,
                sha256=digest,
                archive_path=str(path),
                bytes=len(response.content),
                response_date=response.headers.get("Date"),
                ingested_at=utc_now(),
            )
            response.raise_for_status()
            frame = None
            if name.startswith("sse_"):
                payload = response.json()
                frame = pd.DataFrame(payload["result"])
                total = payload.get("pageHelp", {}).get("total", len(frame))
                r["reported_total"] = total
                r["pagination_complete"] = int(total) == len(frame)
            elif name.startswith("szse_") and name != "szse_suspension_202603":
                frame = pd.read_excel(BytesIO(response.content), dtype=str)
                r["pagination_complete"] = True
            elif name == "bse_page0":
                raw = response.text
                payload = json.loads(raw[raw.find("[") : raw.rfind("]") + 1])[0]
                frame = pd.DataFrame(payload["content"])
                r.update(
                    total_pages=payload["totalPages"],
                    pagination_complete=payload["totalPages"] <= 1,
                )
            if frame is not None:
                if frame.empty:
                    raise ValueError(
                        "empty listing response is not evidence of zero members"
                    )
                out = CACHE / "discovery" / f"{name}_{digest[:12]}.parquet"
                out.parent.mkdir(parents=True, exist_ok=True)
                frame.to_parquet(out, index=False)
                r.update(
                    parsed_rows=len(frame),
                    columns=list(frame.columns),
                    parsed_path=str(out),
                )
            r["status"] = "observed_not_historical_certification"
        except Exception as exc:
            r.update(status="BLOCKED", error=type(exc).__name__ + ": " + str(exc)[:300])
        append_receipt(receipts, r)
        print(
            name,
            r["status"],
            r.get("parsed_rows", r.get("http_status", "")),
            flush=True,
        )
        time.sleep(1)


if __name__ == "__main__":
    main()
