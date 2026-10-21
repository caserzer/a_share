"""Public HTTP capture with one request per provider per second and resumable receipts."""

import json
import time
from pathlib import Path
from urllib.parse import urlparse
import requests
from archive import archive_bytes, append_receipt, utc_now, sha, write_json
from backfill_rpc import PUBLIC


class CapturedHTTP:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        self.last = {}

    def fetch(self, source_id, url, params=None, data=None, method="GET", referer=None):
        host = urlparse(url).netloc
        delay = 1 - (time.monotonic() - self.last.get(host, 0))
        if delay > 0:
            time.sleep(delay)
        self.last[host] = time.monotonic()
        rec = dict(
            source_id=source_id,
            url=url,
            params=params,
            data=data,
            method=method,
            source_observed_at=utc_now(),
            quality_tier="Historical-proxy",
            known_at=None,
        )
        try:
            r = self.session.request(
                method,
                url,
                params=params,
                data=data,
                timeout=(8, 30),
                headers={"Referer": referer or f"https://{host}/"},
            )
            p, h = archive_bytes(r.content)
            rec.update(
                http_status=r.status_code,
                archive_path=str(p),
                sha256=h,
                bytes=len(r.content),
                ingested_at=utc_now(),
                duration_seconds=round(time.monotonic() - self.last[host], 3),
            )
            append_receipt(PUBLIC / "http_attempts.jsonl", rec)
            if r.status_code in (401, 403, 429):
                raise PermissionError(
                    f"{host} returned {r.status_code}; stop this provider"
                )
            r.raise_for_status()
            return r.content, rec
        except Exception as exc:
            if "http_status" not in rec:
                rec.update(error=type(exc).__name__ + ": " + str(exc)[:250])
                append_receipt(PUBLIC / "http_attempts.jsonl", rec)
            raise


def historical_attempts():
    from archive import EP

    paths = [
        EP / "outputs/audits/source_attempts.jsonl",
        EP / "outputs/audits/backfill_source_attempts.jsonl",
    ]
    result = []
    for path in paths:
        if path.exists():
            result.extend(json.loads(x) for x in path.read_text().splitlines())
    return result


def write_partition(frame, path, receipt):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError("append-only source partition exists")
    frame.to_parquet(path, index=False)
    receipt = {
        **receipt,
        "parquet_sha256": sha(path),
        "parquet_path": str(path),
        "rows": len(frame),
    }
    write_json(str(path) + ".receipt.json", receipt)
    return receipt
