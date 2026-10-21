"""Read-only replay of a frozen release. No fetches or cache rewrites."""

import argparse
import json
from pathlib import Path
import pandas as pd
from archive import sha
from pit import FactStore


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--release", type=Path, required=True)
    args = p.parse_args()
    root = args.release
    receipt = json.loads((root / "COMPLETE.json").read_text())
    public = root / "provenance/outputs/manifests/delivery_manifest.json"
    assert sha(public) == receipt["public_delivery_sha256"]
    for r in json.loads(public.read_text())["files"]:
        path = root / "provenance" / r["path"]
        # Documentation/requirements live in the public repo; everything materialized
        # under provenance is verified independently of its working counterpart.
        assert path.exists() and sha(path) == r["sha256"], r["path"]
    records = pd.read_csv(
        root / "provenance/outputs/manifests/local_cache_manifest.csv"
    )
    for r in records.itertuples():
        assert sha(root / r.relative_path) == r.sha256, r.relative_path
    identity = FactStore.from_parquet(
        root / "identity/facts.parquet", archive_root=root / "raw/sha256"
    )
    vintages = FactStore.from_parquet(
        root / "vintages/facts.parquet", archive_root=root / "raw/sha256"
    )
    security = vintages.facts.iloc[0].security_id
    field = vintages.facts.iloc[0].field
    assert vintages.get_asof(security, field, "2024-07-31 15:00").value == 91685852.54
    assert vintages.get_asof(security, field, "2024-08-01 15:00").value == 37014048.62
    print(
        json.dumps(
            dict(
                release_id=receipt["release_id"],
                products_verified=len(records),
                identity_records=len(identity.facts),
                real_financial_replay=True,
                read_only=True,
            )
        )
    )


if __name__ == "__main__":
    main()
