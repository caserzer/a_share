"""Fill missing old raw histories, including BSE candidates. Preserve provider-date scope."""

import argparse
import json
from pathlib import Path
import pandas as pd
from py_mini_racer import py_mini_racer
from akshare.stock.stock_zh_a_sina import hk_js_decode
from archive import sha, write_json, append_receipt
from backfill_rpc import V2, PUBLIC
from backfill_http import CapturedHTTP, historical_attempts, write_partition


def decode_history(body, engine):
    text = body.decode("utf-8-sig")
    raw = text.split("=", 1)[1].split(";", 1)[0].strip().strip('"')
    records = engine.call("d", raw)
    f = pd.DataFrame(records)
    if f.empty:
        raise ValueError("empty decoded raw history")
    f["date"] = (
        pd.to_datetime(f.date, utc=True)
        .dt.tz_convert("Asia/Shanghai")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    f = f[f.date.between("2017-01-03", "2026-10-21")].copy()
    if f.empty:
        raise ValueError("no quotes within requested window")
    if f.date.duplicated().any():
        raise ValueError("duplicate provider-date observations")
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        if col in f:
            f[col] = pd.to_numeric(f[col], errors="coerce")
    return f.sort_values("date").reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    inv = pd.read_parquet(V2 / "inventory/securities.parquet")
    # Acquire missing histories, not thousands of redundant full histories already cached.
    old = pd.read_csv(PUBLIC.parent / "audits/quote_security_coverage.csv")
    missing = set(old.loc[old.source.eq("missing"), "instrument"])
    early_end = set(
        old.loc[
            old.rows.gt(0)
            & old.is_delisted.eq(False)
            & pd.to_datetime(old.last_price).lt("2026-05-22"),
            "instrument",
        ]
    )
    need = inv[
        inv.instrument.isin(missing)
        | inv.instrument.isin(early_end)
        | ~inv.instrument.isin(old.instrument)
        | inv.exchange.eq("BJ")
    ]
    need = need[
        need.delist_date.isna() | need.delist_date.ge("2017-01-03")
    ].sort_values(["exchange", "instrument"])
    if args.limit:
        need = need.head(args.limit)
    http = CapturedHTTP()
    engine = py_mini_racer.MiniRacer()
    engine.eval(hk_js_decode)
    prior = {
        r["source_id"]: r for r in historical_attempts() if r.get("http_status") == 200
    }
    completed = []
    failed = []
    for row in need.itertuples():
        path = V2 / f"acquired/sina/{row.instrument}.parquet"
        receiptpath = Path(str(path) + ".receipt.json")
        if path.exists() and receiptpath.exists():
            r = json.loads(receiptpath.read_text())
            if sha(path) != r["parquet_sha256"]:
                raise ValueError("cached raw partition changed")
            completed.append(row.instrument)
            continue
        url = f"https://finance.sina.com.cn/realstock/company/{row.instrument.lower()}/hisdata_klc2/klc_kl.js"
        try:
            sample = {
                "SH688001": "sina_star_sample",
                "BJ920001": "sina_bse_sample",
            }.get(row.instrument)
            if sample in prior:
                r = prior[sample]
                body = Path(r["archive_path"]).read_bytes()
            else:
                body, r = http.fetch("sina_raw_" + row.instrument, url)
            f = decode_history(body, engine)
            f["instrument"] = row.instrument
            f["quality_tier"] = "Historical-proxy"
            f["market_scope"] = (
                "BSE_OR_NEEQ_UNRESOLVED_UNTIL_LISTING_PROOF"
                if row.exchange == "BJ"
                else "A_SHARE_VENDOR_HISTORY"
            )
            f["source_sha256"] = r["sha256"]
            r = write_partition(
                f,
                path,
                {**r, "transform_sha256": sha(__file__), "historical_known_at": None},
            )
            completed.append(row.instrument)
            append_receipt(
                PUBLIC / "sina_progress.jsonl",
                dict(
                    instrument=row.instrument,
                    status="ACQUIRED",
                    rows=len(f),
                    first_date=str(f.date.min().date()),
                    last_date=str(f.date.max().date()),
                    source_sha256=r["sha256"],
                ),
            )
            print(
                "sina",
                len(completed) + len(failed),
                "/",
                len(need),
                row.instrument,
                len(f),
                flush=True,
            )
        except PermissionError as exc:
            write_json(
                PUBLIC / "sina_permission_stop.json",
                dict(status="BLOCKED_PERMISSION", reason=str(exc)),
            )
            raise
        except Exception as exc:
            failed.append(
                dict(
                    instrument=row.instrument,
                    error=type(exc).__name__ + ": " + str(exc)[:250],
                )
            )
            append_receipt(
                PUBLIC / "sina_progress.jsonl",
                dict(
                    instrument=row.instrument, status="UNRESOLVED", error=str(exc)[:250]
                ),
            )
    write_json(
        PUBLIC / "sina_acquisition.json",
        dict(
            queued=len(need),
            completed=len(completed),
            failed=failed,
            proxy_only=True,
            BSE_history_not_automatically_A_share_history=True,
        ),
    )
    print("Sina acquired", len(completed), "/", len(need), flush=True)


if __name__ == "__main__":
    main()
