"""Sina forward factor capture, fixed cadence, original bytes and bounded stops.

qfq OHLC = unadjusted OHLC / vendor qfq divisor (same method as AkShare).
No eval, no filling missing factor with one, no cross-security factor inheritance.
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from archive import append_receipt, archive_bytes, sha, utc_now, write_json
from v5_core import PUBLIC, V5, baseline, pin_sources, price_input


def parse_factors(body, instrument):
    text = body.decode("utf-8-sig").strip()
    prefix = "var " + instrument.lower() + "qfq="
    if not text.startswith(prefix):
        raise ValueError("unexpected factor response identifier")
    # The static JS can append an opaque /* comment */ after the assignment.
    # Decode exactly one JSON object; never execute trailing JavaScript.
    payload = text[len(prefix):].lstrip()
    obj, end = json.JSONDecoder().raw_decode(payload)
    trailing = payload[end:].strip().lstrip(";").strip()
    if trailing and not (trailing.startswith("/*") and trailing.endswith("*/")):
        raise ValueError("unexpected trailing JavaScript")
    rows = obj.get("data")
    if not rows:
        raise ValueError("empty factor series is not proof of no corporate actions")
    frame = pd.DataFrame(rows).rename(columns={"d": "date", "f": "qfq_divisor"})
    frame = frame[["date", "qfq_divisor"]]
    frame["date"] = pd.to_datetime(frame.date, errors="raise")
    frame["qfq_divisor"] = pd.to_numeric(frame.qfq_divisor, errors="raise")
    if frame.date.duplicated().any() or not np.isfinite(frame.qfq_divisor).all() or not frame.qfq_divisor.gt(0).all():
        raise ValueError("ambiguous or nonpositive factor")
    if obj.get("total") is not None and int(obj["total"]) != len(frame):
        raise ValueError("truncated factor series")
    return frame.sort_values("date").reset_index(drop=True)


def apply_factors(raw, factors, cutoff="2026-10-21"):
    """Use backward asof only. Missing pre-first-factor observations remain missing."""
    result = raw.sort_values("date").copy()
    f = factors[factors.date.le(pd.Timestamp(cutoff))].sort_values("date")
    if f.empty:
        for col in ["open", "high", "low", "close"]:
            result["qfq_" + col] = np.nan
        result["qfq_divisor"] = np.nan
        result["factor_effective_date"] = pd.NaT
        return result
    result = pd.merge_asof(result, f.rename(columns={"date": "factor_effective_date"}),
                           left_on="date", right_on="factor_effective_date", direction="backward")
    for col in ["open", "high", "low", "close"]:
        result["qfq_" + col] = pd.to_numeric(result[col], errors="coerce") / result.qfq_divisor
    return result


def queue():
    inv = pd.read_parquet(baseline("normalized/securities.parquet"))
    instruments = set(inv.instrument)
    intervals = pd.read_parquet(baseline("normalized/code_intervals.parquet"))
    instruments.update(intervals.instrument)
    # Preserve old BSE aliases as candidates, without assuming relisting continuity.
    old = pd.read_parquet(baseline("inputs/baseline/normalized/code_intervals.parquet"))
    if "instrument" in old:
        instruments.update(old.instrument)
    elif "code" in old:
        instruments.update("BJ" + old.code.astype(str).str.zfill(6))
    elif "historical_instrument" in old:
        instruments.update(old.historical_instrument)
    return sorted(instruments)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    PUBLIC.mkdir(parents=True, exist_ok=True)
    versions = pin_sources()
    config = json.loads((Path(__file__).resolve().parents[1] / "configs/pit_v5.json").read_text())
    interval = config["sina_factor_minimum_interval_seconds"]
    todo = queue()
    if args.limit:
        todo = todo[:args.limit]
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn/"})
    last = 0.0
    done = failed = 0
    consecutive = 0
    stop = V5 / "provider_gates/finance.sina.com.cn.stop"
    if stop.exists():
        raise PermissionError("provider previously refused access")
    for i, instrument in enumerate(todo):
        target = V5 / f"acquired/factors/{instrument}.parquet"
        receipt = Path(str(target) + ".receipt.json")
        failure = V5 / f"acquired/factors/{instrument}.unresolved.json"
        if target.exists() and receipt.exists():
            rec = json.loads(receipt.read_text())
            assert sha(target) == rec["parquet_sha256"]
            done += 1
            continue
        if failure.exists():
            failed += 1
            continue
        rec = dict(instrument=instrument, url=f"https://finance.sina.com.cn/realstock/company/{instrument.lower()}/qfq.js",
                   capture_source_hashes=versions, minimum_interval_seconds=interval, quality_tier="Historical-proxy", known_at=None)
        for attempt in range(1, 4):
            time.sleep(max(0, interval - (time.monotonic() - last)))
            last = time.monotonic()
            attempt_rec = dict(rec, attempt=attempt, source_observed_at=utc_now())
            response = None
            try:
                response = session.get(rec["url"], timeout=(8, 25))
                path, digest = archive_bytes(response.content, root=V5)
                attempt_rec.update(http_status=response.status_code, archive_path=str(path), sha256=digest,
                                   bytes=len(response.content), ingested_at=utc_now())
                append_receipt(PUBLIC / "factor_attempts.jsonl", attempt_rec)
                if response.status_code in (401, 403, 429, 567):
                    stop.parent.mkdir(parents=True, exist_ok=True)
                    stop.write_text(str(response.status_code))
                    raise PermissionError("provider refused: " + str(response.status_code))
                response.raise_for_status()
                factors = parse_factors(response.content, instrument)
                target.parent.mkdir(parents=True, exist_ok=True)
                factors.to_parquet(target, index=False)
                write_json(receipt, dict(attempt_rec, parquet_sha256=sha(target), rows=len(factors)))
                done += 1
                consecutive = 0
                break
            except PermissionError:
                raise
            except (ValueError, json.JSONDecodeError) as exc:
                # A complete malformed/empty body has been retained. Repeating it is not useful.
                failure.parent.mkdir(parents=True, exist_ok=True)
                write_json(failure, dict(attempt_rec, reason=str(exc)))
                failed += 1
                break
            except Exception as exc:
                append_receipt(PUBLIC / "factor_attempts.jsonl", dict(attempt_rec, error=str(exc)))
                if response is not None and response.status_code == 404:
                    failure.parent.mkdir(parents=True, exist_ok=True)
                    write_json(failure, dict(attempt_rec, reason=str(exc)))
                    failed += 1
                    break
                if attempt == 3:
                    failure.parent.mkdir(parents=True, exist_ok=True)
                    write_json(failure, dict(attempt_rec, reason=str(exc)))
                    failed += 1
                    consecutive += 1
                else:
                    time.sleep([3, 8][attempt - 1])
        if consecutive >= 3:
            raise RuntimeError("three consecutive transport failures; stopped")
        progress = dict(processed=i+1, queued=len(todo), acquired=done, unresolved=failed,
                        latest_instrument=instrument, updated_at=utc_now())
        write_json(PUBLIC / "factor_checkpoint.json", progress)
        if (i+1) % 50 == 0 or i < 3:
            print(json.dumps(progress), flush=True)
    write_json(PUBLIC / "factor_acquisition.json", dict(queued=len(todo), acquired=done, unresolved=failed, completed_at=utc_now()))


if __name__ == "__main__":
    main()
