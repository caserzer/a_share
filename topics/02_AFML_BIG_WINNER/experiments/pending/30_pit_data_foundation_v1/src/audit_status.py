"""Separate name/ST evidence, trade eligibility unknowns, and missing bar reasons."""

import pandas as pd
from archive import EP, TOPIC, CACHE, sha, write_json


def main():
    out = EP / "outputs/audits"
    q = pd.read_csv(out / "quote_security_coverage.csv")
    sz = TOPIC / "data/raw/akshare/status/stock_info_sz_change_name_short.csv"
    f = pd.read_csv(sz, dtype={"证券代码": str})
    events = pd.DataFrame(
        dict(
            instrument="SZ" + f["证券代码"].str.zfill(6),
            effective_date=pd.to_datetime(f["变更日期"], errors="coerce"),
            old_name=f["变更前简称"],
            new_name=f["变更后简称"],
        )
    )
    # 证券简称 is today's alias. Only 变更后简称 can describe the historical event.
    events["is_st_after_event"] = events.new_name.str.contains(
        r"\*?ST", case=False, regex=True, na=False
    )
    events["quality_tier"] = "Historical-proxy"
    events["source_sha256"] = sha(sz)
    events["known_at"] = pd.NaT
    events["reason"] = "DATED_VENDOR_NAME_EVENT_NO_ORIGINAL_RISK_NOTICE_TIME"
    target = CACHE / "status/sz_name_events.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    events.to_parquet(target, index=False)
    events.groupby(
        [events.effective_date.dt.year.rename("year"), "is_st_after_event"]
    ).size().rename("events").reset_index().to_csv(
        out / "sz_name_events_by_year.csv", index=False
    )
    sh = []
    for p in sorted((TOPIC / "data/raw/akshare/status/sh_name_history").glob("*.csv")):
        f = pd.read_csv(p)
        names = f["name"] if "name" in f else f.get("曾用简称", pd.Series(dtype=str))
        sh.append(
            dict(
                instrument=p.stem,
                rows=len(f),
                has_ST_name=bool(names.str.contains("ST", case=False, na=False).any()),
                schema="|".join(f.columns),
                schema_supported="name" in f or "曾用简称" in f,
                dated=False,
                first_available_certified=False,
                source_sha256=sha(p),
            )
        )
    pd.DataFrame(sh).to_csv(out / "sh_undated_name_evidence.csv", index=False)
    # No exchange suspension archive has been reconciled security/day-wide. Missing
    # observations are not automatically called suspensions.
    missing = q[
        [
            "instrument",
            "board",
            "missing_listed_sessions",
            "source",
            "expected_listed_sessions",
        ]
    ].copy()
    missing["missing_reason"] = missing.source.map(
        lambda s: "SOURCE_FAILURE_EVIDENCE_ONLY_TRADING_STATUS_UNKNOWN"
        if s == "missing"
        else "UNKNOWN_NOT_INFERRED_SUSPENSION"
    )
    missing.to_csv(out / "missing_price_classification.csv", index=False)
    write_json(
        out / "status_summary.json",
        dict(
            sz_name_event_rows=len(events),
            sz_ST_transition_rows=int(events.is_st_after_event.sum()),
            sh_undated_name_files=len(sh),
            sh_lifetime_ST_names=sum(x["has_ST_name"] for x in sh),
            complete_ST_risk_notice_intervals=0,
            complete_suspension_status_sessions=0,
            price_limit_regime_history_certified=False,
            independent_human_review_rate=None,
            eligibility_status="BLOCKED",
            future_lifetime_ST_not_used_for_D2_membership=True,
        ),
    )
    print("status audit complete", len(events), len(sh), flush=True)


if __name__ == "__main__":
    main()
