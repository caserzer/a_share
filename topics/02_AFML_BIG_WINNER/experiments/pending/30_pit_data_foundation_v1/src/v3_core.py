"""Independent append-only v3 evidence capture. V1/v2 releases are read-only inputs."""

import json
import time
from pathlib import Path
from urllib.parse import urlparse
import requests
import pandas as pd
import fcntl
from archive import CACHE, EP, archive_bytes, append_receipt, sha, utc_now, write_json

V3 = CACHE / "pit_v3"
PUBLIC3 = EP / "outputs/pit_v3"
V2_RELEASE = (
    CACHE
    / "backfill_v2/releases/d24febaf36b968c2f8f0653633ed4a10a514db91a87c9af76dc37549a99db3a2"
)
CUTOFF = "2026-10-21"


class Capture:
    def __init__(self):
        archive_bytes(Path(__file__).read_bytes())
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        self.last = {}
        self.stopped = set()

    def fetch(self, source_id, url, params=None, data=None, method="GET"):
        host = urlparse(url).netloc
        # Public static document CDN only; dynamic disclosure APIs stay at 1/s.
        # A shared gate enforces this across workers, with refusal stopping the host.
        interval = 0.25 if host == "pdf.dfcfw.com" else 1.0
        gates = V3 / "provider_gates"
        gates.mkdir(parents=True, exist_ok=True)
        stop = gates / (host + ".stop")
        if host in self.stopped or stop.exists():
            raise PermissionError("provider previously refused access")
        for attempt in range(1, 4):
            with (gates / (host + ".clock")).open("a+") as clock:
                fcntl.flock(clock, fcntl.LOCK_EX)
                clock.seek(0)
                delay = interval - (time.time() - float(clock.read() or "0"))
                if delay > 0:
                    time.sleep(delay)
                clock.seek(0)
                clock.truncate()
                clock.write(str(time.time()))
                clock.flush()
            self.last[host] = time.monotonic()
            r = dict(
                source_id=source_id,
                url=url,
                params=params,
                data=data,
                method=method,
                source_observed_at=utc_now(),
                attempt=attempt,
                minimum_host_interval_seconds=interval,
            )
            try:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    headers={"Referer": f"https://{host}/"},
                    timeout=(8, 40),
                )
                path, digest = archive_bytes(response.content)
                r.update(
                    http_status=response.status_code,
                    archive_path=str(path),
                    sha256=digest,
                    ingested_at=utc_now(),
                    bytes=len(response.content),
                )
                append_receipt(PUBLIC3 / "source_attempts.jsonl", r)
                if response.status_code in (401, 403, 429, 567):
                    self.stopped.add(host)
                    stop.write_text(str(response.status_code))
                    raise PermissionError(
                        f"provider refused with HTTP {response.status_code}"
                    )
                response.raise_for_status()
                return response.content, r
            except PermissionError:
                raise
            except Exception as exc:
                if "http_status" not in r:
                    append_receipt(
                        PUBLIC3 / "source_attempts.jsonl",
                        dict(**r, error=str(exc)[:250]),
                    )
                if attempt == 3:
                    raise
                time.sleep([3, 8][attempt - 1])


def save(frame, path, receipt):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError("append-only acquired partition exists")
    frame.to_parquet(path, index=False)
    write_json(
        str(path) + ".receipt.json",
        dict(**receipt, rows=len(frame), parquet_sha256=sha(path)),
    )


def read_verified(path):
    path = Path(path)
    receipt = json.loads(Path(str(path) + ".receipt.json").read_text())
    if sha(path) != receipt["parquet_sha256"]:
        raise ValueError("changed acquired partition")
    digest = receipt["sha256"]
    source = CACHE / "raw/sha256" / digest[:2] / digest
    if sha(source) != digest:
        raise ValueError("changed original bytes")
    return pd.read_parquet(path), receipt


def inventory():
    return pd.read_parquet(V2_RELEASE / "normalized/securities.parquet")


def code_version(path):
    return archive_bytes(Path(path).read_bytes())[1]


def documents(group):
    """Append-only attachment recoveries supersede failed guessed H2 routes."""
    records = {}
    for folder in [
        V3 / f"documents/{group}",
        V3 / f"documents/attachment_recovery/{group}",
    ]:
        for p in sorted(folder.glob("*.json")):
            records[p.stem] = (p, json.loads(p.read_text()))
    return [records[k] for k in sorted(records)]
