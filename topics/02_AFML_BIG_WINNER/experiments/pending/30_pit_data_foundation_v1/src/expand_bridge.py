"""Full provisional D2 membership overlay, including newly observed official securities.

The legacy-window compatibility projection remains separate. Added members have
UNKNOWN labels, never borrowed D1 returns. No claim of complete historical population.
"""

import pandas as pd
from archive import EP, TOPIC, CACHE, write_json


def expand_membership(inventory, origins, legacy):
    rows = []
    for r in inventory.itertuples():
        dates = origins[origins >= r.listing_date]
        if pd.notna(r.delist_date):
            dates = dates[dates < r.delist_date]
        rows.extend(
            dict(
                date=date,
                instrument=r.instrument,
                security_id=r.security_id,
                board=r.board_bucket,
                D2_provisional_member=True,
            )
            for date in dates
        )
    candidate = pd.DataFrame(rows)
    if candidate.duplicated(["date", "instrument"]).any():
        raise ValueError("ambiguous identity episodes cannot be merged by current code")
    fields = [c for c in legacy if not c.startswith("D2_")]
    out = candidate.merge(
        legacy[fields], on=["date", "instrument"], how="outer", validate="one_to_one"
    )
    for c in ["D0_member", "D1_member", "D2_provisional_member"]:
        out[c] = out[c].astype("boolean").fillna(False)
    out["D2_added_vs_D1"] = out.D2_provisional_member & ~out.D1_member
    out["D2_strict_member"] = False
    out["D2_strict_member_reason"] = "HISTORICAL_POPULATION_AND_STATUS_NOT_CERTIFIED"
    for policy in ["price", "total", "executable"]:
        out["D2_" + policy + "_label"] = float("nan")
    out["D2_label_reason"] = (
        "UNVERIFIED_EXECUTION_AND_RIGHTS_NO_LEGACY_LABEL_SUBSTITUTION"
    )
    return out.sort_values(["date", "instrument"]).reset_index(drop=True)


def main():
    calendar = pd.read_csv(
        TOPIC / "data/qlib/cn_data_pit_largecap/calendars/day.txt",
        header=None,
        names=["date"],
    )
    calendar["date"] = pd.to_datetime(calendar.date)
    (CACHE / "calendar").mkdir(exist_ok=True)
    calendar.to_parquet(CACHE / "calendar/sessions.parquet", index=False)
    inv = pd.read_parquet(CACHE / "identity/security_inventory.parquet")
    old = pd.read_parquet(CACHE / "bridge/security_month_labels.parquet")
    origins = pd.DatetimeIndex(sorted(old.date.unique()))
    full = expand_membership(inv, origins, old)
    full.to_parquet(
        CACHE / "bridge/security_month_labels_expanded.parquet", index=False
    )
    summary = full.groupby("instrument", as_index=False).agg(
        D0_origins=("D0_member", "sum"),
        D1_origins=("D1_member", "sum"),
        D2_provisional_origins=("D2_provisional_member", "sum"),
        D2_added_origins=("D2_added_vs_D1", "sum"),
        D0_legacy_known=("y_6", "count"),
        D1_legacy_known=("actual", "count"),
        D2_total_known=("D2_total_label", "count"),
    )
    summary = inv[["instrument", "security_id", "board_bucket"]].merge(
        summary, on="instrument", how="left"
    )
    for c in summary.columns[3:]:
        summary[c] = summary[c].fillna(0).astype(int)
    summary.to_csv(EP / "outputs/audits/bridge_expanded_by_security.csv", index=False)
    full.groupby("date", as_index=False).agg(
        D0_origins=("D0_member", "sum"),
        D1_origins=("D1_member", "sum"),
        D2_provisional_origins=("D2_provisional_member", "sum"),
        D2_added_origins=("D2_added_vs_D1", "sum"),
        D2_total_known=("D2_total_label", "count"),
    ).to_csv(EP / "outputs/audits/bridge_expanded_by_month.csv", index=False)
    write_json(
        EP / "outputs/audits/expanded_bridge_summary.json",
        dict(
            rows=len(full),
            legacy_projection_rows=len(old),
            added_provisional_origins=int(full.D2_added_vs_D1.sum()),
            added_securities_with_origins=int(summary.D2_added_origins.gt(0).sum()),
            securities_in_inventory=len(inv),
            D2_provisional_origins=int(full.D2_provisional_member.sum()),
            first_origin=str(origins.min().date()),
            last_origin=str(origins.max().date()),
            later_period="BLOCKED_NO_VERIFIED_OHLCV_STATUS_RIGHTS_AND_ACTUAL_CLOSED_SESSION_CALENDAR",
            added_labels_known=0,
            population_certified=False,
        ),
    )
    print(
        "expanded D2 bridge",
        len(full),
        "origins; added",
        int(full.D2_added_vs_D1.sum()),
        flush=True,
    )


if __name__ == "__main__":
    main()
