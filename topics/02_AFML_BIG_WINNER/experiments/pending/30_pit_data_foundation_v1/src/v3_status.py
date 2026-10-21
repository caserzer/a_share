"""Compare original effective boundaries, preserve conflicts and qualify events."""

import json
import pandas as pd
from archive import write_json
from v3_core import V3, PUBLIC3, V2_RELEASE, inventory, code_version


def build():
    current = pd.read_parquet(V3 / "normalized/status_facts.parquet")
    baseline = pd.read_parquet(V2_RELEASE / "normalized/reviewed_facts.parquet")
    facts = pd.concat([current, baseline], ignore_index=True)
    facts["decoded_value"] = facts.value.map(json.loads)
    inv = inventory()
    rows = []
    for r in inv.itertuples():
        f = facts[facts.security_id.eq(r.security_id)]
        end = f[f.field.eq("listed") & f.decoded_value.eq(False)]
        starts = f[f.field.eq("listed") & f.decoded_value.eq(True)]
        dates = sorted(set(end.effective_time.dt.tz_localize(None).dt.normalize()))
        if not dates and not r.identity_date_conflict and not r.is_delisted:
            continue
        unique = len(dates) == 1
        same = (
            unique
            and not pd.isna(r.delist_date)
            and pd.Timestamp(r.delist_date) == dates[0]
        )
        rows.append(
            dict(
                security_id=r.security_id,
                instrument=r.instrument,
                board_bucket=r.board_bucket,
                metadata_listing_date=r.listing_date,
                metadata_delist_date=r.delist_date,
                v2_identity_date_conflict=bool(r.identity_date_conflict),
                original_termination_date=dates[0] if unique else None,
                original_termination_date_candidates=json.dumps(
                    [str(d.date()) for d in dates]
                ),
                date_resolution="ORIGINAL_AGREES_WITH_METADATA"
                if same
                else "ORIGINAL_DISAGREES_WITH_METADATA"
                if unique and not pd.isna(r.delist_date)
                else "ORIGINAL_TERMINATION_WITHOUT_METADATA"
                if unique
                else "CONFLICTING_ORIGINAL_DATES_BLOCKED"
                if dates
                else "NO_EXPLICIT_ORIGINAL_TERMINATION_DATE",
                original_source_sha256s=json.dumps(sorted(set(end.source_sha256))),
                first_conservative_known_at=str(end.known_at.min())
                if len(end)
                else None,
                positive_relisting_events=len(starts),
                source_page_status_events=len(f),
                continuous_daily_qualification_coverage_attested=False,
                original_listing_date_or_identity_episode_still_requires_its_own_evidence=True,
            )
        )
    frame = pd.DataFrame(rows)
    frame.to_parquet(
        V3 / "normalized/original_lifecycle_boundaries.parquet", index=False
    )
    frame.to_csv(PUBLIC3 / "original_lifecycle_boundaries.csv", index=False)
    updated = inv.copy()
    updated["metadata_delist_date_v2"] = updated.delist_date
    proved = frame[frame.original_termination_date.notna()].set_index("security_id")
    corrected = updated.security_id.map(proved.original_termination_date)
    updated["v3_original_termination_date"] = pd.to_datetime(corrected)
    updated["delist_date"] = updated.v3_original_termination_date.combine_first(
        updated.delist_date
    )
    updated["is_delisted"] = updated.delist_date.notna()
    updated["complete_historical_eligibility_attested"] = False
    updated.to_parquet(V3 / "normalized/securities.parquet", index=False)
    pd.DataFrame(
        facts.groupby(["field", facts.effective_time.dt.year]).size()
    ).reset_index().rename(
        columns={0: "facts", "effective_time": "effective_year"}
    ).to_csv(PUBLIC3 / "status_events_by_year.csv", index=False)
    write_json(
        PUBLIC3 / "historical_qualification_summary.json",
        dict(
            original_status_event_facts=len(current),
            securities_with_original_status_events=current.security_id.nunique(),
            unique_original_termination_dates=int(
                frame.original_termination_date.notna().sum()
            ),
            boundary_resolutions=frame.date_resolution.value_counts().to_dict(),
            full_daily_qualification_coverage_attested=0,
            listing_identity_conflicts_not_silently_cleared=True,
            transform_sha256=code_version(__file__),
        ),
    )


if __name__ == "__main__":
    build()
