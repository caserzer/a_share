"""Three original-proven continuous A-share code changes; no org-id-only merges."""

import json
from pathlib import Path

import pandas as pd

from archive import archive_bytes, sha, write_json
from v4_core import PUBLIC, V4, baseline, source_bytes
from v4_pipeline import calendar, original_pages

VERSION = archive_bytes(Path(__file__).read_bytes(), root=V4)[1]
CASES = [
    ("SZ000022", "SZ001872", "2018-12-26", "AN201812251279607605", [1, 4]),
    ("SZ000043", "SZ001914", "2019-12-16", "AN201912151371852474", [1, 3]),
    ("SZ300114", "SZ302132", "2025-02-17", "AN202502141643087427", [1, 2]),
]


def slice_price_aliases(old, new, effective):
    """Never use both aliases on one date or retain an expired code's quotes."""
    first, second = old.copy(), new.copy()
    first["date"] = pd.to_datetime(first.date)
    second["date"] = pd.to_datetime(second.date)
    boundary = pd.Timestamp(effective)
    first = first[first.date < boundary]
    second = second[second.date >= boundary]
    result = pd.concat([first, second], ignore_index=True).sort_values("date")
    if result.date.duplicated().any():
        raise ValueError("code interval overlap")
    return result


def build():
    (V4 / "normalized").mkdir(parents=True, exist_ok=True)
    original = pd.read_parquet(baseline("normalized/securities.parquet"))
    inv = original.copy().set_index("security_id", drop=False)
    cal = calendar()
    index = {
        a["art_code"]: a
        for a in [
            json.loads(s)
            for s in pd.read_parquet(
                baseline("indices/identity_complete.parquet")
            ).announcement
        ]
    }
    pinned = {
        x["art_code"]: x
        for x in json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "configs/v4_code_change_page_reviews.json"
            ).read_text()
        )
    }
    redirects, intervals, snapshots = [], [], []
    inv["metadata_instrument_v3"] = inv.instrument
    inv["metadata_delist_date_v3"] = inv.delist_date
    inv["code_change_original_sha256"] = None
    for old, new, date, art, pages in CASES:
        a, b = (
            original[original.instrument.eq(old)].iloc[0],
            original[original.instrument.eq(new)].iloc[0],
        )
        doc = json.loads((V4 / f"documents/identity/{art}.json").read_text())
        source = doc["source"]
        review = pinned[art]
        if (
            source["sha256"] != review["source_sha256"]
            or sha(source_bytes(source)) != review["source_sha256"]
        ):
            raise ValueError("reviewed identity original changed")
        for image in review["images"]:
            if sha(V4 / image["path"]) != image["sha256"]:
                raise ValueError("reviewed identity image changed")
        text = "".join("".join(p.split()) for p in original_pages(source))
        if not all(
            x in text
            for x in [
                old[2:],
                new[2:],
                "公司法人主体存续",
                "上市主体没有发生实质变化",
                "持有",
                "股份数量不变",
            ]
        ):
            raise ValueError("not an attested simple continuous code change")
        pub = index[art]["notice_date"][:10]
        known = cal.publication_time(pub)
        redirects.append(
            dict(
                legacy_security_id=b.security_id,
                canonical_security_id=a.security_id,
                old_instrument=old,
                new_instrument=new,
                effective_date=date,
                notice_date=pub,
                known_at=str(known),
                art_code=art,
                source_sha256=source["sha256"],
                index_sha256=index[art]["index_sha256"],
                old_vendor_delist_date=str(a.delist_date.date()),
                same_legal_listing_entity=True,
                share_quantity_unchanged_by_code_change=True,
                complete_action_ledger_attested=False,
                independent_human_review=False,
                transform_sha256=VERSION,
            )
        )
        inv.loc[a.security_id, "instrument"] = new
        inv.loc[a.security_id, "code"] = new[2:]
        inv.loc[a.security_id, "name"] = b["name"]
        inv.loc[a.security_id, "delist_date"] = pd.NaT
        inv.loc[a.security_id, "is_delisted"] = False
        inv.loc[a.security_id, "code_change_original_sha256"] = source["sha256"]
        inv = inv.drop(index=b.security_id)
        for instrument, start, end in [
            (old, str(a.listing_date.date()), date),
            (new, date, None),
        ]:
            intervals.append(
                dict(
                    security_id=a.security_id,
                    instrument=instrument,
                    valid_from=start,
                    valid_until_exclusive=end,
                    boundary_known_at=str(known),
                    source_sha256=source["sha256"],
                    art_code=art,
                    retrospective_identity_reconstruction=True,
                    full_daily_qualification_attested=False,
                )
            )
        frames = []
        for row in [a, b]:
            name = f"normalized/prices/{row.security_id}.parquet"
            try:
                path = baseline(name)
            except ValueError as exc:
                if "undeclared baseline input" not in str(exc):
                    raise
                path = baseline("baseline/" + name)
            frame = pd.read_parquet(path)
            frame["code_interval_source_instrument"] = row.instrument
            frame["code_interval_source_security_id_v3"] = row.security_id
            frames.append(frame)
        combined = slice_price_aliases(frames[0], frames[1], date)
        combined["security_id"] = a.security_id
        combined["code_change_original_sha256"] = source["sha256"]
        path = V4 / f"normalized/prices/{a.security_id}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_parquet(path, index=False)
        snapshots.append(
            dict(
                canonical_security_id=a.security_id,
                rows=len(combined),
                first_date=str(combined.date.min().date()),
                last_date=str(combined.date.max().date()),
                sha256=sha(path),
            )
        )
    inv.reset_index(drop=True).to_parquet(
        V4 / "normalized/securities.parquet", index=False
    )
    pd.DataFrame(redirects).to_parquet(
        V4 / "normalized/security_id_redirects.parquet", index=False
    )
    pd.DataFrame(redirects).to_csv(
        PUBLIC / "code_change_identity_reviews.csv", index=False
    )
    pd.DataFrame(intervals).to_parquet(
        V4 / "normalized/code_intervals.parquet", index=False
    )
    pd.DataFrame(intervals).to_csv(PUBLIC / "code_intervals.csv", index=False)
    collisions = original[
        original.org_id.notna() & original.org_id.duplicated(keep=False)
    ].copy()
    collision_orgs = set(
        original[original.instrument.isin([x[0] for x in CASES])].org_id
    )
    collisions["v4_disposition"] = collisions.org_id.map(
        lambda x: (
            "ORIGINAL_PROVEN_CONTINUOUS_CODE_CHANGE"
            if x in collision_orgs
            else "DISTINCT_EPISODES_OR_TRANSFER_OR_RELISTING_REQUIRES_ORIGINAL_EVENT_LEDGER"
        )
    )
    collisions.to_csv(PUBLIC / "shared_issuer_id_audit.csv", index=False)
    write_json(
        PUBLIC / "identity_summary.json",
        dict(
            baseline_inventory_rows=len(original),
            canonical_inventory_rows=len(inv),
            confirmed_continuous_code_changes=len(redirects),
            false_retirements_removed=3,
            original_remaining_retired_since_2017=int(
                inv.delist_date.ge("2017-01-03").sum()
            ),
            org_id_collision_groups=collisions.org_id.nunique(),
            unresolved_org_id_collision_groups=collisions.org_id.nunique() - 3,
            shared_org_id_alone_never_used_to_merge=True,
            price_paths=snapshots,
            transform_sha256=VERSION,
        ),
    )


if __name__ == "__main__":
    build()
