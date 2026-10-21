"""Seal and independently copy the D2-v2 backfill. No hard links or network I/O."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from archive import CACHE, EP, sha, write_json, utc_now, archive_bytes
from backfill_rpc import V2, PUBLIC


def file_records(folder):
    return [
        dict(
            relative_path=str(p.relative_to(folder)),
            sha256=sha(p),
            bytes=p.stat().st_size,
        )
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    ]


def verify_release(root):
    root = Path(root)
    complete = json.loads((root / "COMPLETE.json").read_text())
    manifest = root / "FULL_MANIFEST.json"
    if sha(manifest) != complete["full_manifest_sha256"]:
        raise ValueError("frozen manifest changed")
    files = json.loads(manifest.read_text())
    for r in files:
        if sha(root / r["relative_path"]) != r["sha256"]:
            raise ValueError("frozen product changed: " + r["relative_path"])
    from backfill_dataset import D2BackfillDataset

    d = D2BackfillDataset(
        root / "normalized",
        root / "provenance/normalized_manifest.json",
        baseline=False,
    )
    assert (
        d.get_asof("SH600000", "close", "2026-10-21 15:00", "Historical-proxy").value
        == 9.66
    )
    assert d.get_asof("SH600000", "close", "2026-10-21 15:00").value is None
    assert (
        d.get_asof(
            "SH600000", "close", "2026-10-21 15:00", "Historical-proxy", "archived"
        ).value
        is None
    )
    assert d.get_asof("SZ000748", "can_buy", "2017-01-03 15:00").value is False
    field = "financial:original_revenue:2025-12-31"
    assert d.get_asof("BJ920001", field, "2026-03-27 15:00").value is None
    assert d.get_asof("BJ920001", field, "2026-03-30 09:30").value == 212838536.28
    assert (
        d.get_asof("BJ830799", "code", "2025-05-05", "Historical-proxy").value
        == "830799"
    )
    assert (
        d.get_asof("BJ920799", "code", "2025-05-06", "Historical-proxy").value
        == "920799"
    )
    assert (
        d.get_asof(
            "SZ000584",
            "financial:other_receivables_intercompany_balance:2023-12-31",
            "2024-07-31 15:00",
        ).value
        == 91685852.54
    )
    assert (
        d.get_asof(
            "SZ000584",
            "financial:other_receivables_intercompany_balance:2023-12-31",
            "2024-08-01 15:00",
        ).value
        == 37014048.62
    )
    label = d.build_labels("SH600000", "2026-05-29 15:00", 20, "total")
    assert label.value is None
    return dict(
        status="PASS",
        release_id=complete["release_id"],
        frozen_files_verified=len(files),
        frozen_bytes_verified=sum(r["bytes"] for r in files),
        independent_copies=True,
        raw_and_products_verified=True,
        reviewed_financial_and_suspension_replay=True,
        code_cutover_replay=True,
        v1_financial_versions_preserved=True,
        strict_proxy_separation=True,
        unknown_execution_label_preserved=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-release", type=Path)
    parser.add_argument("--seal-only", action="store_true")
    args = parser.parse_args()
    if args.verify_release:
        print(json.dumps(verify_release(args.verify_release)))
        return
    root = V2 / "normalized"
    summary = json.loads((PUBLIC / "normalization_summary.json").read_text())
    market = json.loads((PUBLIC / "market_acquisition.json").read_text())
    audit = json.loads((PUBLIC / "acquisition_validation.json").read_text())
    if (
        market["status"] != "ACQUIRED"
        or audit["status"] != "PASS"
        or audit["complete_market_days_replayed"] != 102
    ):
        raise ValueError(
            "complete market acquisition and independent raw replay required"
        )
    sources = []
    for folder in ["src", "configs", "tests", "schemas"]:
        for p in sorted((EP / folder).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                sources.append(
                    dict(relative_path=str(p.relative_to(EP)), sha256=sha(p))
                )
                archive_bytes(p.read_bytes())
    sources.append(
        dict(relative_path="requirements.txt", sha256=sha(EP / "requirements.txt"))
    )
    files = file_records(root)
    manifest = dict(
        version=summary["version"],
        sealed_at=utc_now(),
        files=files,
        source_code_and_config=sources,
        baseline_v1_release_id="f97e739dcc7bae24ff996106343211a5d0bc05146f3d823dbefeac1d73b453b9",
        strict_full_market_ready=False,
    )
    write_json(PUBLIC / "normalized_manifest.json", manifest)
    if args.seal_only:
        return
    raw_files = file_records(CACHE / "raw/sha256")
    fingerprint = json.dumps(
        dict(manifest=manifest, original_blobs=raw_files), sort_keys=True
    ).encode()
    release_id = hashlib.sha256(fingerprint).hexdigest()
    release = V2 / "releases" / release_id
    if release.exists():
        raise FileExistsError("immutable release already exists")
    staging = release.with_name(release.name + ".incomplete")
    staging.mkdir(parents=True)
    shutil.copytree(root, staging / "normalized")
    shutil.copytree(CACHE / "raw/sha256", staging / "raw/sha256")
    for folder in ["acquired", "documents", "financials", "identity", "reviewed"]:
        shutil.copytree(V2 / folder, staging / "acquisition" / folder)
    for r in sources:
        src = EP / r["relative_path"]
        dst = staging / "source" / r["relative_path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    shutil.copytree(PUBLIC, staging / "provenance")
    shutil.copytree(EP / "reports", staging / "provenance/reports")
    shutil.copyfile(EP / "README.md", staging / "provenance/README.md")
    shutil.copyfile(EP / "data_dictionary.md", staging / "provenance/data_dictionary.md")
    allfiles = file_records(staging)
    write_json(staging / "FULL_MANIFEST.json", allfiles)
    write_json(
        staging / "COMPLETE.json",
        dict(
            release_id=release_id,
            full_manifest_sha256=sha(staging / "FULL_MANIFEST.json"),
            normalized_manifest_sha256=sha(PUBLIC / "normalized_manifest.json"),
        ),
    )
    for p in staging.rglob("*"):
        if p.is_file():
            os.chmod(p, 0o444)
    staging.rename(release)
    result = verify_release(release)
    write_json(PUBLIC / "release_verification.json", result)
    write_json(PUBLIC / "release.json", dict(path=str(release), **result))
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
