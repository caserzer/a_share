"""V4 extension: verified frozen v3 inputs, independent source bytes and stops."""

import json
import shutil
import time
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

import requests

from archive import CACHE, EP, append_receipt, archive_bytes, sha, utc_now

BASE_ID = "7aa946f77a7702afb4c4adcd4fb5e2db9a9a1aa64fad7d17f97095fa3d5b2012"
BASE = CACHE / "pit_v3/releases" / BASE_ID
V4 = CACHE / "pit_v4"
PUBLIC = EP / "outputs/pit_v4"
CAPTURE_VERSION = archive_bytes(Path(__file__).read_bytes(), root=V4)[1]


@lru_cache(maxsize=1)
def baseline_files():
    complete = json.loads((BASE / "COMPLETE.json").read_text())
    manifest = BASE / "FULL_MANIFEST.json"
    if sha(manifest) != complete["full_manifest_sha256"]:
        raise ValueError("changed baseline manifest")
    return {r["relative_path"]: r["sha256"] for r in json.loads(manifest.read_text())}


def baseline(name):
    """Copy only verified dependencies; subsequent replay uses private copies."""
    target = V4 / "inputs" / name
    files = baseline_files()
    if name not in files:
        raise ValueError("undeclared baseline input: " + name)
    source = target if target.exists() else BASE / name
    if sha(source) != files[name]:
        raise ValueError("changed baseline input: " + name)
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        append_receipt(
            V4 / "input_manifest.jsonl",
            dict(relative_path=name, sha256=files[name], baseline_release=BASE_ID),
        )
    return target


def source_bytes(record):
    digest = record["sha256"]
    path = V4 / "raw/sha256" / digest[:2] / digest
    if path.exists():
        if sha(path) != digest:
            raise ValueError("changed v4 original")
        return path
    # V3's own flat source pool contains all baseline response bytes.
    prior = baseline("raw/sha256/" + digest[:2] + "/" + digest)
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(prior, path)
    return path


def original_document(art, expected_sha256):
    for group in ["retirement", "core", "financial"]:
        for name in [
            f"documents/attachment_recovery/{group}/{art}.json",
            f"documents/{group}/{art}.json",
        ]:
            if name not in baseline_files():
                continue
            record = json.loads(baseline(name).read_text())
            if (
                record.get("status") == "ORIGINAL_PDF_RECOVERED"
                and record["source"]["sha256"] == expected_sha256
            ):
                return record
    raise ValueError("no verified baseline original metadata for " + art)


class Capture:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        self.last = {}

    def fetch(self, source_id, url, data=None, method="GET"):
        host = urlparse(url).netloc
        stop = V4 / "provider_gates" / (host + ".stop")
        inherited = CACHE / "pit_v3/provider_gates" / (host + ".stop")
        if (
            host in {"np-cnotice-stock.eastmoney.com", "www.neeq.com.cn"}
            or stop.exists()
            or inherited.exists()
        ):
            raise PermissionError("provider previously refused access")
        interval = 0.25 if host == "pdf.dfcfw.com" else 1.0
        for attempt in range(1, 4):
            delay = interval - (time.monotonic() - self.last.get(host, 0))
            if delay > 0:
                time.sleep(delay)
            self.last[host] = time.monotonic()
            r = dict(
                source_id=source_id,
                url=url,
                method=method,
                data=data,
                attempt=attempt,
                source_observed_at=utc_now(),
                minimum_interval_seconds=interval,
                capture_transform_sha256=CAPTURE_VERSION,
            )
            try:
                response = self.session.request(method, url, data=data, timeout=(8, 40))
                path, digest = archive_bytes(response.content, root=V4)
                r.update(
                    http_status=response.status_code,
                    archive_path=str(path),
                    sha256=digest,
                    bytes=len(response.content),
                    ingested_at=utc_now(),
                )
                append_receipt(PUBLIC / "source_attempts.jsonl", r)
                if response.status_code in (401, 403, 429, 567):
                    stop.parent.mkdir(parents=True, exist_ok=True)
                    stop.write_text(str(response.status_code))
                    raise PermissionError("provider refused access")
                response.raise_for_status()
                return response.content, r
            except PermissionError:
                raise
            except Exception as exc:
                if "http_status" not in r:
                    append_receipt(
                        PUBLIC / "source_attempts.jsonl",
                        dict(**r, error=str(exc)[:250]),
                    )
                if attempt == 3:
                    raise
                time.sleep([3, 8][attempt - 1])


def transform():
    return archive_bytes(Path(__file__).read_bytes(), root=V4)[1]
