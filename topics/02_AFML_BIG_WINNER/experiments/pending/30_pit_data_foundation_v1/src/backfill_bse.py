"""Recover BSE official current list through its working disclosure host.

The source's pre-November-2021 listing field can mean NEEQ selected-tier entry.
It must never overwrite actual BSE listing evidence or become historical shares.
"""

import json
import pandas as pd
from archive import write_json
from backfill_http import CapturedHTTP, write_partition
from backfill_build import verified
from backfill_rpc import V2, PUBLIC


def main():
    http = CapturedHTTP()
    page = 0
    pages = 1
    frames = []
    hashes = []
    expected = None
    while page < pages:
        path = V2 / f"acquired/bse_official/pages/{page:03d}.parquet"
        if path.exists():
            f, r = verified(path)
            pages = r["reported_pages"]
            total = r["reported_total"]
        else:
            b, r = http.fetch(
                "BSE_official_current_securities",
                "https://www.bseinfo.net/nqxxController/nqxxCnzq.do",
                method="POST",
                data={
                    "page": str(page),
                    "typejb": "T",
                    "xxfcbj[]": "2",
                    "xxzqdm": "",
                    "sortfield": "xxzqdm",
                    "sorttype": "asc",
                },
            )
            text = b.decode()
            data = json.loads(text[text.index("[") : text.rindex("]") + 1])[0]
            f = pd.DataFrame(data["content"])
            pages = int(data["totalPages"])
            total = int(data["totalElements"])
            r.update(reported_pages=pages, reported_total=total)
            write_partition(f, path, r)
        if expected is None:
            expected = total
        if total != expected:
            raise ValueError("official current list changed during pagination")
        f["source_sha256"] = r["sha256"]
        f["source_observed_at"] = r["source_observed_at"]
        frames.append(f)
        hashes.append(r["sha256"])
        page += 1
    f = pd.concat(frames, ignore_index=True)
    if len(f) != expected or f.xxzqdm.duplicated().any():
        raise ValueError("official current BSE list incomplete or duplicated")
    f.to_parquet(V2 / "acquired/bse_official_current.parquet", index=False)
    inv = pd.read_parquet(V2 / "inventory/securities.parquet")
    observed = set("BJ" + f.xxzqdm.astype(str))
    candidates = inv[inv.exchange.eq("BJ")].copy()
    candidates["in_official_current_BSE_list"] = candidates.instrument.isin(observed)
    candidates[
        ["instrument", "security_id", "name", "in_official_current_BSE_list"]
    ].to_csv(PUBLIC / "bse_official_current_reconciliation.csv", index=False)
    write_json(
        PUBLIC / "bse_official_source_summary.json",
        dict(
            official_current_securities=len(f),
            reported_rows=expected,
            complete_pages=pages,
            candidates_not_current=candidates.loc[
                ~candidates.in_official_current_BSE_list, "instrument"
            ].tolist(),
            current_not_in_provisional_inventory=sorted(
                observed - set(candidates.instrument)
            ),
            raw_response_sha256=hashes,
            asof_date="2026-10-21",
            historical_membership_certified=False,
            current_shares_not_backfilled=True,
            source_listing_date_may_be_NEEQ_date=True,
        ),
    )
    print("official BSE current list", len(f), "complete", flush=True)


if __name__ == "__main__":
    main()
