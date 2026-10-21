"""Fill the missing post-May market window; optionally fetch all historical daily states.

Each complete day has a preserved raw TCP frame and parsed Parquet receipt.
Interrupted work resumes from verified complete files, without zero-filled days.
"""

import argparse
import json
import pandas as pd
from archive import sha, write_json, append_receipt, utc_now
from backfill_rpc import V2, PUBLIC, PublicRPC


def valid_cache(path):
    receipt = path.with_suffix(path.suffix + ".receipt.json")
    if not path.exists() or not receipt.exists():
        return False
    return sha(path) == json.loads(receipt.read_text())["parquet_sha256"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--full-history", action="store_true")
    args = p.parse_args()
    client = PublicRPC()
    calpath = V2 / "acquired/calendar.parquet"
    if not valid_cache(calpath):
        f, r = client.call(
            "query_trade_dates", start_date="2017-01-03", end_date="2026-10-21"
        )
        client.save(f, r, calpath)
    cal = pd.read_parquet(calpath)
    dates = pd.to_datetime(cal.loc[cal.is_trading_day.eq("1"), "calendar_date"])
    recent = dates[dates.ge("2026-05-25")].sort_values(ascending=False)
    prior = (
        dates[dates.lt("2026-05-25")].sort_values(ascending=False)
        if args.full_history
        else pd.DatetimeIndex([])
    )
    queue = list(recent) + list(prior)
    failed = []
    completed = 0
    consecutive = 0
    for i, date in enumerate(queue):
        key = str(date.date())
        path = V2 / f"acquired/daily/{key}.parquet"
        if valid_cache(path):
            completed += 1
            continue
        try:
            f, r = client.call("query_daily_history_k_AStock", date=key)
            if not f.date.eq(key).all():
                raise ValueError("wrong-date response")
            if not f.adjustflag.eq("3").all():
                raise ValueError("adjusted data refused")
            if f.code.duplicated().any():
                raise ValueError("duplicate securities in daily response")
            client.save(f, r, path)
            completed += 1
            consecutive = 0
            append_receipt(
                PUBLIC / "market_progress.jsonl",
                dict(
                    date=key,
                    status="ACQUIRED",
                    rows=len(f),
                    parquet_sha256=r["parquet_sha256"],
                    response_sha256=r["response_sha256"],
                ),
            )
            print("market", i + 1, "/", len(queue), key, "rows", len(f), flush=True)
        except PermissionError as exc:
            write_json(
                PUBLIC / "market_permission_stop.json",
                dict(date=key, status="BLOCKED_PERMISSION", reason=str(exc)),
            )
            raise
        except Exception as exc:
            failed.append(dict(date=key, error=str(exc)[:250]))
            consecutive += 1
            append_receipt(
                PUBLIC / "market_progress.jsonl",
                dict(date=key, status="UNRESOLVED", error=str(exc)[:250]),
            )
            if consecutive >= 3:
                break
        write_json(
            PUBLIC / "market_checkpoint.json",
            dict(
                completed=completed,
                queued=len(queue),
                failed=failed,
                latest_processed=key,
                full_history=args.full_history,
                updated_at=utc_now(),
            ),
        )
    write_json(
        PUBLIC / "market_acquisition.json",
        dict(
            completed=completed,
            queued=len(queue),
            failed=failed,
            requested_start="2017-01-03" if args.full_history else "2026-05-25",
            requested_end="2026-10-21",
            status="ACQUIRED" if completed == len(queue) else "PARTIAL",
            completed_at=utc_now(),
        ),
    )
    print("market acquisition complete", completed, "/", len(queue), flush=True)


if __name__ == "__main__":
    main()
