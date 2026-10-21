"""BSE code intervals from official mapping and two distinct code-cutover notices."""

import json
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd
from archive import sha, write_json
from backfill_rpc import V2, PUBLIC


def main():
    official = pd.read_parquet(V2 / "acquired/bse_official_code_mapping.parquet")
    official.columns = [
        "number",
        "name",
        "NEEQ_or_listing_date",
        "old_code",
        "new_code",
    ]
    official = official[official.old_code.astype(str).str.fullmatch(r"\d{6}")].copy()
    raw = json.loads(
        (V2 / "acquired/bse_official_code_mapping.parquet.receipt.json").read_text()
    )
    pilot = json.loads((V2 / "documents/bse_pilot_code_mapping.json").read_text())
    if sha(pilot["archive_path"]) != pilot["sha256"]:
        raise ValueError("changed original code mapping document")
    xml = ET.fromstring(
        zipfile.ZipFile(pilot["archive_path"]).read("word/document.xml")
    )
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    pilot_rows = [
        ["".join(c.itertext()) for c in tr.findall("w:tc", ns)]
        for tr in xml.findall(".//w:tr", ns)
    ][1:]
    pilot_map = {r[3]: r[4] for r in pilot_rows}
    if len(pilot_map) != 6:
        raise ValueError("pilot mapping must identify six securities")
    inv = pd.read_parquet(V2 / "inventory/securities.parquet").set_index("instrument")
    source_first = json.loads(
        (V2 / "documents/bse_code_cutover_200025603.json").read_text()
    )
    source_rest = json.loads(
        (V2 / "documents/bse_code_cutover_200026735.json").read_text()
    )
    rows = []
    for r in official.itertuples():
        instrument = "BJ" + str(r.new_code)
        if instrument not in inv.index:
            raise ValueError("official alias absent from provisional inventory")
        first = str(r.old_code) in pilot_map
        if first and pilot_map[str(r.old_code)] != str(r.new_code):
            raise ValueError("pilot and current official mapping disagree")
        date = "2025-05-06" if first else "2025-10-09"
        source = source_first if first else source_rest
        sid = inv.loc[instrument, "security_id"]
        for code, start, end in [
            (str(r.old_code), None, date),
            (str(r.new_code), date, None),
        ]:
            rows.append(
                dict(
                    security_id=sid,
                    canonical_instrument=instrument,
                    historical_instrument="BJ" + code,
                    valid_from=start,
                    valid_to=end,
                    interval_boundary="valid_from_inclusive_valid_to_exclusive",
                    membership_start_separate_from_code_interval=True,
                    mapping_sha256=raw["sha256"],
                    cutover_notice_sha256=source["sha256"],
                    pilot_original_mapping_sha256=pilot["sha256"] if first else None,
                    quality_tier="Historical-proxy",
                    reason="OFFICIAL_CURRENT_MAPPING_PLUS_ORIGINAL_CUTOVER_NOTICE_MAPPING_FIRST_VERSION_NOT_BLANKET_CERTIFIED",
                )
            )
    f = pd.DataFrame(rows)
    f["valid_from"] = pd.to_datetime(f.valid_from)
    f["valid_to"] = pd.to_datetime(f.valid_to)
    out = V2 / "identity/code_intervals.parquet"
    out.parent.mkdir(exist_ok=True)
    f.to_parquet(out, index=False)
    f.to_csv(PUBLIC / "bse_historical_code_intervals.csv", index=False)
    write_json(
        PUBLIC / "bse_code_interval_summary.json",
        dict(
            official_mapped_issuers=len(official),
            explicit_intervals=len(f),
            pilot_issuers=len(pilot_map),
            pilot_effective="2025-05-06",
            remaining_effective="2025-10-09",
            mapping_source_uri=raw["url"],
            mapping_source_sha256=raw["sha256"],
            all_old_aliases_share_stable_security_id=True,
            code_interval_does_not_prove_listing_or_execution=True,
            strict_historical_mapping_first_version_certified=False,
        ),
    )


if __name__ == "__main__":
    main()
