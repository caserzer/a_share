"""Bounded public BaoStock RPC with original wire archive and reconnect-on-failure.

Uses the provider's public anonymous account only. No API keys or personal
credentials are read. Incomplete TCP frames never contaminate the next query.
"""

from __future__ import annotations
import importlib
from pathlib import Path
import socket
import sys
import time
import zlib
import pandas as pd
from archive import EP, CACHE, archive_bytes, append_receipt, sha, utc_now, write_json

V2 = CACHE / "backfill_v2"
PUBLIC = EP / "outputs/backfill_v2"


def enable_sdk():
    try:
        return importlib.import_module("baostock")
    except ImportError:
        sys.path.insert(0, str(V2 / "vendor"))
        return importlib.import_module("baostock")


class PublicRPC:
    def __init__(self, log_name="baostock_attempts.jsonl"):
        self.bs = enable_sdk()
        import baostock.common.context as ctx
        import baostock.common.contants as cons
        import baostock.util.socketutil as transport

        self.ctx, self.cons = ctx, cons
        self.current = {"method": "login", "params": {}}
        self.log = PUBLIC / log_name
        self.last_start = 0.0
        self.responses = []
        self.connected = False
        transport.send_msg = self._send
        socket.setdefaulttimeout(30)

    def _send(self, message):
        delay = 1.0 - (time.monotonic() - self.last_start)
        if delay > 0:
            time.sleep(delay)
        self.last_start = time.monotonic()
        receipt = dict(
            provider="BaoStock_public_anonymous",
            method=self.current["method"],
            params=self.current["params"],
            source_observed_at=utc_now(),
            endpoint=f"tcp://{self.cons.BAOSTOCK_SERVER_IP}:{self.cons.BAOSTOCK_SERVER_PORT}",
            quality_tier="Historical-proxy",
            known_at=None,
        )
        try:
            stream = self.ctx.default_socket
            stream.settimeout(30)
            stream.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            stream.sendall((message + "\n").encode())
            chunks = []
            total = 0
            deadline = time.monotonic() + 90
            while True:
                chunk = stream.recv(262144)
                if not chunk:
                    raise ConnectionError("provider closed incomplete frame")
                chunks.append(chunk)
                total += len(chunk)
                if total > 50_000_000:
                    raise ValueError("response size bound exceeded")
                if b"".join(chunks[-2:]).endswith(b"<![CDATA[]]>\n"):
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError("RPC overall deadline exceeded")
            wire = b"".join(chunks)
            path, digest = archive_bytes(wire)
            receipt.update(
                archive_path=str(path),
                sha256=digest,
                bytes=len(wire),
                ingested_at=utc_now(),
                transport_status="COMPLETE_FRAME",
                duration_seconds=round(time.monotonic() - self.last_start, 3),
            )
            header = wire[: self.cons.MESSAGE_HEADER_LENGTH].decode("utf-8")
            fields = header.split(self.cons.MESSAGE_SPLIT)
            if fields[1] in self.cons.COMPRESSED_MESSAGE_TYPE_TUPLE:
                length = int(fields[2])
                body = zlib.decompress(
                    wire[
                        self.cons.MESSAGE_HEADER_LENGTH : self.cons.MESSAGE_HEADER_LENGTH
                        + length
                    ]
                ).decode("utf-8")
                result = header + body
            else:
                result = wire.decode("utf-8")
            self.responses.append(receipt)
            append_receipt(self.log, receipt)
            return result
        except Exception as exc:
            self.connected = False
            try:
                self.ctx.default_socket.close()
            except Exception:
                pass
            receipt.update(
                transport_status="FAILED",
                error=type(exc).__name__ + ": " + str(exc)[:250],
            )
            append_receipt(self.log, receipt)
            self.responses.append(receipt)
            return None

    def login(self):
        self.current = {"method": "login", "params": {}}
        result = self.bs.login()
        self.connected = result.error_code == "0"
        if not self.connected:
            raise ConnectionError(result.error_msg)

    def call(self, method, **params):
        last = None
        for attempt in range(1, 4):
            try:
                if not self.connected:
                    self.login()
                self.current = {"method": method, "params": params}
                self.responses = []
                result = getattr(self.bs, method)(**params)
                if result.error_code != "0":
                    if any(
                        k in result.error_msg.lower()
                        for k in [
                            "api-key",
                            "api key",
                            "权限",
                            "积分",
                            "配额",
                            "额度",
                            "访问受限",
                        ]
                    ):
                        raise PermissionError(result.error_msg)
                    raise ConnectionError(result.error_code + ": " + result.error_msg)
                rows = []
                while result.error_code == "0" and result.next():
                    rows.append(result.get_row_data())
                if result.error_code != "0":
                    raise ConnectionError("pagination failed: " + result.error_msg)
                f = pd.DataFrame(rows, columns=result.fields)
                if f.empty:
                    raise ValueError(
                        "empty successful response is not zero population evidence"
                    )
                source_hashes = [r["sha256"] for r in self.responses if r.get("sha256")]
                if not source_hashes:
                    raise ValueError("no original response retained")
                return f, dict(
                    method=method,
                    params=params,
                    rows=len(f),
                    response_sha256=source_hashes,
                    observed_at=self.responses[0]["source_observed_at"],
                    ingested_at=self.responses[-1]["ingested_at"],
                    transform_sha256=sha(__file__),
                    quality_tier="Historical-proxy",
                )
            except PermissionError:
                raise
            except Exception as exc:
                last = exc
                self.connected = False
                try:
                    self.ctx.default_socket.close()
                except Exception:
                    pass
                append_receipt(
                    self.log,
                    dict(
                        method=method,
                        params=params,
                        attempt=attempt,
                        status="RETRY_OR_UNRESOLVED",
                        error=type(exc).__name__ + ": " + str(exc)[:250],
                        observed_at=utc_now(),
                    ),
                )
                if attempt < 3:
                    time.sleep([5, 15][attempt - 1])
        raise RuntimeError(str(last))

    def save(self, frame, metadata, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError(
                "append-only acquired table already exists: " + str(path)
            )
        frame.to_parquet(path, index=False)
        metadata.update(
            parquet_path=str(path), parquet_sha256=sha(path), bytes=path.stat().st_size
        )
        write_json(str(path) + ".receipt.json", metadata)
        return metadata
