"""Rebuild the full denominator and strict labels after three identity corrections."""

import json
import shutil
from pathlib import Path

import pandas as pd

from archive import archive_bytes, sha, write_json
import v3_bridge
from v4_core import PUBLIC, V4, baseline, baseline_files
from v4_review import fact

VERSION = archive_bytes(Path(__file__).read_bytes(), root=V4)[1]


def prepare():
    # Exact frozen normalized inputs are sufficient to replay the bridge offline.
    names = [
        n
        for n in baseline_files()
        if n.startswith("baseline/normalized/prices/") and n.endswith(".parquet")
    ]
    for n in names:
        baseline(n)
    for n in [
        "baseline/normalized/calendar.parquet",
        "baseline/normalized/legacy_bridge_with_v2_quote_availability.parquet",
    ]:
        baseline(n)
    for name in baseline_files():
        if name.startswith("normalized/prices/") and name.endswith(".parquet"):
            source = baseline(name)
            target = V4 / name
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    states = pd.read_parquet(baseline("normalized/status_facts.parquet"))
    reviewed = pd.read_parquet(V4 / "normalized/status_reviewed_facts.parquet")
    redirects = pd.read_parquet(V4 / "normalized/security_id_redirects.parquet")
    lookup = dict(zip(redirects.legacy_security_id, redirects.canonical_security_id))
    states["security_id"] = states.security_id.map(lambda x: lookup.get(x, x))
    code_events = []
    for r in redirects.to_dict("records"):
        doc = json.loads((V4 / f"documents/identity/{r['art_code']}.json").read_text())
        code_events.append(
            fact(
                r["canonical_security_id"],
                "identity:code_change",
                r["new_instrument"],
                r["effective_date"],
                r["known_at"],
                r["art_code"],
                doc["source"],
                r["index_sha256"],
                "code",
                "Original-proven continuous listed entity and unchanged held share quantity; not a delisting or a new IPO; no positive execution flag",
            )
        )
    from pit import FactStore

    target = V4 / "normalized/code_change_facts.parquet"
    FactStore(code_events).to_parquet(target)
    combined = pd.concat([states, reviewed, pd.read_parquet(target)], ignore_index=True)
    if combined.record_id.duplicated().any():
        raise ValueError("state record id collision")
    combined.to_parquet(V4 / "normalized/status_facts.parquet", index=False)
    return redirects


def historical_instruments(frame, redirects, column):
    for r in redirects.itertuples():
        mask = frame.security_id.eq(r.canonical_security_id)
        frame.loc[mask, column] = frame.loc[mask, "date"].map(
            lambda d: (
                r.old_instrument
                if pd.Timestamp(d) < pd.Timestamp(r.effective_date)
                else r.new_instrument
            )
        )
    return frame


def build():
    redirects = prepare()
    helper = baseline("source/src/v3_bridge.py")
    if sha(helper) != sha(v3_bridge.__file__):
        raise ValueError("changed frozen bridge helper")
    v3_bridge.V3 = V4
    v3_bridge.PUBLIC3 = PUBLIC
    v3_bridge.V2_RELEASE = V4 / "inputs/baseline"
    v3_bridge.code_version = lambda path: sha(path)
    v3_bridge.main()
    path = V4 / "normalized/full_monthly_bridge.parquet"
    bridge = pd.read_parquet(path)
    bridge = bridge.rename(
        columns={c: c.replace("v3_", "v4_", 1) for c in bridge if c.startswith("v3_")}
    )
    historical_instruments(bridge, redirects, "v4_instrument")
    lookup = dict(zip(redirects.legacy_security_id, redirects.canonical_security_id))
    bridge["v4_canonical_security_id"] = bridge.security_id.map(
        lambda x: lookup.get(x, x)
    )
    bridge["v4_retained_legacy_alias_row"] = bridge.security_id.ne(
        bridge.v4_canonical_security_id
    )
    if bridge.loc[bridge.v4_retained_legacy_alias_row, "v4_provisional_member"].any():
        raise ValueError("retained legacy alias double counted as canonical member")
    bridge.to_parquet(path, index=False)
    summary = json.loads((PUBLIC / "full_bridge_summary.json").read_text())
    summary.update(
        bridge_sha256=sha(path),
        v4_wrapper_transform_sha256=VERSION,
        code_change_identity_source_sha256s=redirects.source_sha256.tolist(),
        legacy_alias_rows_retained=int(bridge.v4_retained_legacy_alias_row.sum()),
        legacy_rows_preserved_without_rekeying=True,
        historical_origin_codes_not_current_code_backfill=True,
    )
    for artifact in summary["labels"]:
        p = V4 / artifact["path"]
        f = pd.read_parquet(p)
        historical_instruments(f, redirects, "instrument")
        f.to_parquet(p, index=False)
        artifact["sha256"] = sha(p)
    old = json.loads(baseline("provenance/full_bridge_summary.json").read_text())
    summary["v3_candidate_month_rows"] = old["candidate_month_rows"]
    summary["duplicate_security_months_removed"] = (
        old["candidate_month_rows"] - summary["candidate_month_rows"]
    )
    summary["strict_label_rows"] = sum(x["rows"] for x in summary["labels"])
    write_json(PUBLIC / "full_bridge_summary.json", summary)


if __name__ == "__main__":
    build()
