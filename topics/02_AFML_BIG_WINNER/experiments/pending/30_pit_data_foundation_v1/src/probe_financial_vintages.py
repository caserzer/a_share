"""Targeted first/correction-vintage discovery; samples never certify the population."""

import re
import time
import requests
from archive import EP, archive_bytes, append_receipt, utc_now


def fetch(name, url, method="GET", **kwargs):
    receipt = dict(
        source_id=name,
        url=url,
        method=method,
        source_observed_at=utc_now(),
        known_at=None,
        historical_tier="Historical-proxy",
        request=kwargs.get("data"),
    )
    try:
        response = requests.request(
            method,
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.cninfo.com.cn/",
            },
            timeout=(8, 20),
            **kwargs,
        )
        path, digest = archive_bytes(response.content)
        receipt.update(
            archive_path=str(path),
            sha256=digest,
            bytes=len(response.content),
            http_status=response.status_code,
            ingested_at=utc_now(),
        )
        response.raise_for_status()
        receipt["status"] = "observed_not_historical_certification"
        if "query" in name:
            payload = response.json()
            ann = payload.get("announcements") or []
            receipt.update(
                parsed_rows=len(ann),
                total=payload.get("totalAnnouncement"),
                announcements=ann,
            )
            if not ann:
                receipt.update(
                    status="BLOCKED",
                    error="EMPTY_INDEX_NOT_PROOF_OF_NO_HISTORICAL_DISCLOSURES",
                )
        elif not response.content.startswith(b"%PDF"):
            raise ValueError("not PDF bytes")
    except Exception as exc:
        receipt.update(
            status="BLOCKED", error=type(exc).__name__ + ": " + str(exc)[:300]
        )
    append_receipt(EP / "outputs/audits/source_attempts.jsonl", receipt)
    print(
        name,
        receipt["status"],
        receipt.get("parsed_rows", receipt.get("bytes")),
        flush=True,
    )
    time.sleep(1)
    return receipt


def main():
    for name, search in [
        ("cninfo_vintage_query", "2023年年度报告"),
        ("cninfo_issuer_query", "哈工智能"),
    ]:
        fetch(
            name,
            "https://www.cninfo.com.cn/new/hisAnnouncement/query",
            "POST",
            data={
                "pageNum": 1,
                "pageSize": 30,
                "tabName": "fulltext",
                "column": "szse",
                "stock": "",
                "searchkey": search,
                "seDate": "2024-07-31~2024-07-31",
                "isHLtitle": "true",
                "sortName": "time",
                "sortType": "desc",
            },
        )
    fetch(
        "issuer_original_pdf_sina_mirror",
        "https://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESZ_STOCK/2024/2024-4/2024-04-30/10176642.PDF",
    )
    fetch(
        "issuer_correction_pdf_sina_mirror",
        "https://file.finance.sina.com.cn/211.154.219.97:9494/MRGG/CNSESZ_STOCK/2024/2024-7/2024-07-31/10352704.PDF",
    )
    fetch(
        "cninfo_correction_original_pdf",
        "https://static.cninfo.com.cn/finalpage/2024-07-31/1220755916.PDF",
    )
    fetch(
        "cninfo_revised_report_pdf",
        "https://static.cninfo.com.cn/finalpage/2024-07-31/1220755914.PDF",
    )
    index = fetch(
        "cninfo_first_report_query",
        "https://www.cninfo.com.cn/new/hisAnnouncement/query",
        "POST",
        data={
            "pageNum": 1,
            "pageSize": 30,
            "tabName": "fulltext",
            "column": "szse",
            "stock": "000584,gssz0000584",
            "searchkey": "2023年年度报告",
            "seDate": "2024-04-30~2024-04-30",
            "isHLtitle": "true",
        },
    )
    for a in index.get("announcements", []):
        title = re.sub("<[^>]+>", "", a["announcementTitle"])
        if (
            a["secCode"] == "000584"
            and title.endswith("2023年年度报告")
            and "摘要" not in title
        ):
            fetch(
                "cninfo_first_report_original_pdf",
                "https://static.cninfo.com.cn/" + a["adjunctUrl"],
            )


if __name__ == "__main__":
    main()
