"""Resumable public daily acquisition, globally limited to one RPC start/second.

Workers overlap network waits, not request rate. Each worker owns its SDK socket.
Existing verified V2 partitions are read-only dependencies. Raw frames and all new
partitions are isolated in v6. No personal credentials are read.
"""
import argparse
import json
import multiprocessing as mp
import time
import pandas as pd
from pe_common import CACHE, OLD, V5, OUT, daily_path, archive_bytes, write_json, utc_now

def access_denied(message):
    return any(word in (message or '').lower() for word in
               ['黑名单', 'blacklist', '访问受限', '权限不足', '配额', '额度'])

def initialize(lock, next_start):
    global client
    import backfill_rpc as rpc
    rpc.PUBLIC = CACHE / 'logs'
    rpc.archive_bytes = lambda body: archive_bytes(body, root=CACHE)
    class PacedRPC(rpc.PublicRPC):
        def _send(self, message):
            if (CACHE / 'BAOSTOCK_ACCESS_STOP.json').exists():
                raise PermissionError('BaoStock access-stop latch is set')
            with lock:
                delay = next_start.value - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                if (CACHE / 'BAOSTOCK_ACCESS_STOP.json').exists():
                    raise PermissionError('BaoStock access-stop latch is set')
                next_start.value = time.monotonic() + 1.05
            result = super()._send(message)
            if access_denied(result):
                write_json(CACHE / 'BAOSTOCK_ACCESS_STOP.json',
                           dict(status='BLOCKED_ACCESS', observed_at=utc_now(),
                                reason='Provider explicitly denied access; no automatic retries'))
                raise PermissionError('Provider explicitly denied access')
            return result
    client = PacedRPC(log_name=f'worker-{mp.current_process().pid}.jsonl')

def fetch(day):
    try:
        f, r = client.call('query_daily_history_k_AStock', date=day)
        if not f.date.eq(day).all() or not f.adjustflag.eq('3').all():
            raise ValueError('wrong date or adjusted response')
        if f.code.duplicated().any() or 'peTTM' not in f:
            raise ValueError('duplicate code or missing PE field')
        path = CACHE / f'acquired/daily/{day}.parquet'
        client.save(f, r, path)
        return dict(date=day, status='ACQUIRED', rows=len(f))
    except PermissionError:
        raise
    except Exception as exc:
        return dict(date=day, status='UNRESOLVED', error=str(exc)[:250])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=1)
    args = parser.parse_args()
    if (CACHE / 'BAOSTOCK_ACCESS_STOP.json').exists():
        raise PermissionError('Provider access is blocked; contact provider before resuming')
    dates = pd.read_parquet(V5 / 'inputs/inputs/baseline/normalized/calendar.parquet').date
    dates = [str(pd.Timestamp(d).date()) for d in dates]
    missing = [d for d in dates if daily_path(d) is None]
    # Fill the actual EP32 evaluation window first; finish all other sessions too.
    missing.sort(key=lambda d: (not ('2021' <= d[:4] <= '2024'), d))
    reused = len(dates) - len(missing)
    successes, failures = 0, []
    started = utc_now()
    def checkpoint(status):
        write_json(OUT / 'acquisition.json', dict(status=status,
            sessions=len(dates), reused=reused, acquired=successes, failures=failures,
            remaining=len(missing)-successes, started_at=started, updated_at=utc_now(),
            requested_start=dates[0], requested_end=dates[-1],
            request_start_spacing_seconds=1.05, workers=args.workers))
    checkpoint('RUNNING')
    ctx = mp.get_context('spawn')
    lock, next_start = ctx.Lock(), ctx.Value('d', 0.0)
    try:
        with ctx.Pool(args.workers, initialize, (lock, next_start)) as pool:
            for result in pool.imap_unordered(fetch, missing, chunksize=1):
                if result['status'] == 'ACQUIRED':
                    successes += 1
                else:
                    failures.append(result)
                checkpoint('RUNNING')
                if (successes + len(failures)) % 25 == 0 or result['status'] != 'ACQUIRED':
                    print(json.dumps(dict(completed=reused+successes,total=len(dates),**result)), flush=True)
    except PermissionError:
        checkpoint('BLOCKED_ACCESS')
        raise
    checkpoint('ACQUIRED' if not failures else 'PARTIAL')
    print(json.dumps(dict(completed=reused+successes,total=len(dates),failed=len(failures))), flush=True)

if __name__ == '__main__':
    main()
