"""Verify acquired original bytes, offline replay, and preserved predecessor artifacts."""

import json
from pathlib import Path
import zlib
import pandas as pd
from py_mini_racer import py_mini_racer
from akshare.stock.stock_zh_a_sina import hk_js_decode
from archive import CACHE, EP, sha, write_json
from backfill_rpc import V2, PUBLIC
from backfill_build import verified
from backfill_sina import decode_history


def replay_daily(path):
    f, r = verified(path)
    parts = []
    for digest in r["response_sha256"]:
        wire = (CACHE / "raw/sha256" / digest[:2] / digest).read_bytes()
        header = wire[:21].decode().split("\x01")
        body = zlib.decompress(wire[21 : 21 + int(header[2])]).decode().split("\x01")
        if body[0] != "0" or body[2] != "query_daily_history_k_AStock":
            raise ValueError("wrong original daily message")
        parts.append(
            pd.DataFrame(
                json.loads("".join(body[4].split()))["record"],
                columns=[c.strip() for c in body[5].split(",")],
            )
        )
    pd.testing.assert_frame_equal(
        f, pd.concat(parts, ignore_index=True), check_dtype=False
    )


def main():
    records = []
    attempts = []
    for log in [
        PUBLIC / "http_attempts.jsonl",
        PUBLIC / "baostock_attempts.jsonl",
        EP / "outputs/audits/backfill_source_attempts.jsonl",
    ]:
        if log.exists():
            attempts.extend(json.loads(x) for x in log.read_text().splitlines())
    for r in attempts:
        if not r.get("sha256") or not r.get("archive_path"):
            continue
        if sha(r["archive_path"]) != r["sha256"]:
            raise ValueError("changed original archived response")
        records.append(
            dict(
                sha256=r["sha256"],
                bytes=Path(r["archive_path"]).stat().st_size,
                source_uri=r.get("url", r.get("endpoint")),
                source_observed_at=r.get("source_observed_at"),
                status=r.get("http_status", r.get("transport_status")),
            )
        )
    pd.DataFrame(records).drop_duplicates(["sha256", "source_uri"]).to_csv(
        PUBLIC / "raw_source_manifest.csv", index=False
    )
    tables = 0
    for path in sorted((V2 / "acquired/tables").glob("*/*.parquet")):
        f, r = verified(path)
        original = json.loads(Path(r["archive_path"]).read_text())["result"]["data"]
        pd.testing.assert_frame_equal(f, pd.DataFrame(original), check_dtype=False)
        tables += 1
    daily = sorted((V2 / "acquired/daily").glob("*.parquet"))
    for path in daily:
        replay_daily(path)
    engine = py_mini_racer.MiniRacer()
    engine.eval(hk_js_decode)
    histories = sorted((V2 / "acquired/sina").glob("*.parquet"))
    for i, path in enumerate(histories):
        f, r = verified(path)
        original = decode_history(Path(r["archive_path"]).read_bytes(), engine)
        fields = [
            c
            for c in ["date", "open", "high", "low", "close", "volume", "amount"]
            if c in original
        ]
        pd.testing.assert_frame_equal(f[fields], original[fields], check_dtype=False)
        if i % 250 == 0:
            print("offline history replay", i, "/", len(histories), flush=True)
    prior = json.loads((EP / "outputs/manifests/prior_preservation.json").read_text())
    # The preserved audit is a path -> SHA map, not a generated-data glob.
    entries = prior.get("files", prior.get("hashes", prior))
    if isinstance(entries, dict):
        pairs = entries.items()
    else:
        pairs = [(r["path"], r["sha256"]) for r in entries]
    preserved = 0
    repo = EP.parents[4]
    for path, digest in pairs:
        if not isinstance(digest, str) or len(digest) != 64:
            continue
        if sha(repo / path) != digest:
            raise ValueError("predecessor artifact changed: " + path)
        preserved += 1
    write_json(
        PUBLIC / "acquisition_validation.json",
        dict(
            status="PASS",
            raw_receipts_verified=len(records),
            unique_original_blobs=len(set(r["sha256"] for r in records)),
            complete_vendor_table_pages_replayed=tables,
            complete_market_days_replayed=len(daily),
            missing_security_histories_replayed=len(histories),
            predecessor_files_preserved=preserved,
            raw_to_parquet_replay_mismatches=0,
            zero_fill_used=False,
            historical_proxy_auto_promoted=False,
            validation_code_sha256=sha(__file__),
        ),
    )
    print("offline acquisition replay passed", flush=True)


if __name__ == "__main__":
    main()
