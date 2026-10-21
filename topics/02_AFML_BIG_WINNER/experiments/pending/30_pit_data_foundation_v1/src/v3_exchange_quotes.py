"""Archive exchange-hosted raw historical quotes as independent corroboration.

An official current historical service is not silently called an original PIT
vintage. It also does not prove that an opening order would have filled.
"""

import json
import pandas as pd
from archive import write_json
from v3_core import V3, PUBLIC3, V2_RELEASE, Capture, save, read_verified, code_version
from v3_announcements import core_cohort


def main():
    http = Capture()
    version = code_version(__file__)
    coverage = []
    for i, r in enumerate(core_cohort().sort_values("instrument").itertuples()):
        result = dict(
            instrument=r.instrument, security_id=r.security_id, status="UNKNOWN"
        )
        if r.exchange == "BJ":
            result["reason"] = "BSE_NOT_CLAIMED_COVERED_BY_SSE_CROSS_MARKET_SERVICE"
            coverage.append(result)
            continue
        path = V3 / f"acquired/exchange_quotes/{r.instrument}.parquet"
        try:
            if path.exists():
                f, rec = read_verified(path)
            else:
                board = "sh1" if r.exchange == "SH" else "sz1"
                url = (
                    f"https://yunhq.sse.com.cn:32042/v1/{board}/dayk/{r.instrument[2:]}"
                )
                body, rec = http.fetch(
                    "exchange_historical_quotes_" + r.instrument,
                    url,
                    params=dict(begin=-3000, end=-1, period="day"),
                )
                payload = json.loads(body)
                if payload.get("code") != r.instrument[2:]:
                    raise ValueError("wrong or absent instrument response")
                data = payload.get("kline") or []
                if any(len(row) != 7 for row in data):
                    raise ValueError("unrecognized original kline schema")
                f = pd.DataFrame(
                    data,
                    columns=["date", "open", "high", "low", "close", "volume", "money"],
                )
                if len(f):
                    f["date"] = pd.to_datetime(f.date.astype(str), format="%Y%m%d")
                    if f.date.duplicated().any():
                        raise ValueError("duplicate original dates")
                rec.update(
                    transform_sha256=version,
                    provider_reported_total=payload.get("total"),
                    provider_begin=payload.get("begin"),
                    provider_end=payload.get("end"),
                    source_class="OFFICIAL_SSE_HOSTED_CURRENT_HISTORICAL_SERVICE",
                    historical_first_version_certified=False,
                    open_fill_certified=False,
                )
                save(f, path, rec)
            f = f[f.date.between("2017-01-03", "2026-10-21")] if len(f) else f
            result.update(
                status="ACQUIRED",
                rows_in_window=len(f),
                source_sha256=rec["sha256"],
                first_version_certified=False,
                opening_execution_certified=False,
            )
            oldpath = V2_RELEASE / f"normalized/prices/{r.security_id}.parquet"
            if oldpath.exists() and len(f):
                old = pd.read_parquet(oldpath)
                both = f.merge(
                    old[["date", "open", "high", "low", "close", "volume", "money"]],
                    on="date",
                    suffixes=("_official", "_v2"),
                )
                result["overlap_dates"] = len(both)
                for c in ["open", "high", "low", "close", "volume", "money"]:
                    diff = (both[c + "_official"] - both[c + "_v2"]).abs()
                    result[c + "_disagreements"] = int(
                        diff.gt(0.51 if c == "money" else 0.0000001).sum()
                    )
            coverage.append(result)
        except PermissionError:
            raise
        except Exception as exc:
            result["reason"] = type(exc).__name__ + ": " + str(exc)[:200]
            coverage.append(result)
        if i % 25 == 0:
            print(
                "official histories", i + 1, r.instrument, result["status"], flush=True
            )
    pd.DataFrame(coverage).to_csv(
        PUBLIC3 / "exchange_quote_corroboration.csv", index=False
    )
    write_json(
        PUBLIC3 / "exchange_quote_summary.json",
        dict(
            queried=len(coverage),
            acquired=sum(r["status"] == "ACQUIRED" for r in coverage),
            first_vintage_and_open_fill_not_automatically_certified=True,
            transform_sha256=version,
        ),
    )


if __name__ == "__main__":
    main()
