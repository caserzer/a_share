"""Independent private v4 release with a pinned v3 input catalog."""

import argparse
import json
import platform
import shutil
from pathlib import Path

import pandas as pd
import pyarrow

from archive import EP, sha, utc_now, write_json
from v4_core import BASE, BASE_ID, PUBLIC, V4
from v4_dataset import D2V4Dataset


def verify(root):
    root = Path(root)
    complete = json.loads((root / "COMPLETE.json").read_text())
    manifest = root / "FULL_MANIFEST.json"
    assert sha(manifest) == complete["full_manifest_sha256"]
    records = json.loads(manifest.read_text())
    total = 0
    for r in records:
        p = root / r["relative_path"]
        assert p.stat().st_nlink == 1 and sha(p) == r["sha256"]
        total += p.stat().st_size
    data = D2V4Dataset(root)
    field = "financial:reviewed_reported_operating_cash_flow:2018-12-31"
    assert data.get_asof("SZ002680", field, "2019-12-31 15:00").value is None
    assert data.get_asof("SZ002680", field, "2020-11-24 09:30").value == -203122781.04
    assert (
        data.get_asof("SZ002680", field, "2020-11-24 09:30", mode="archived").value
        is None
    )
    assert data.get_asof("SH600290", "listed", "2024-01-23 09:30").value is False
    assert data.get_asof("SZ002776", "listed", "2024-02-02 09:30").value is False
    assert data.get_asof("SZ300114", "trading_code", "2025-02-14 15:00").value is None
    assert (
        data.get_asof("SZ300114", "trading_code", "2025-02-17 15:00").value
        == "SZ302132"
    )
    assert data.build_labels("SZ302132", "2020-01-23", 20, "total")["value"] is None
    assert data.universe_asof("2020-01-23 15:00").empty
    assert not data.snapshot_manifest("2020-01-23")["files"]
    for old, new in [
        ("SZ000022", "SZ001872"),
        ("SZ000043", "SZ001914"),
        ("SZ300114", "SZ302132"),
    ]:
        u = data.universe_asof("2017-01-26 15:00", "Historical-proxy")
        assert u.instrument.eq(old).sum() == 1 and u.instrument.eq(new).sum() == 0
    return dict(
        status="PASS",
        release_id=complete["release_id"],
        path=str(root),
        files_verified=len(records),
        bytes_verified=total,
        independent_copies_no_hardlinks=True,
        source_page_asof_and_canonical_alias_reader_replay=True,
    )


def seal():
    validation = json.loads((PUBLIC / "validation.json").read_text())
    if validation["status"] != "PASS":
        raise ValueError("validation required before seal")
    catalog = V4 / "baseline_catalog"
    catalog.mkdir(exist_ok=True)
    for name in ["FULL_MANIFEST.json", "COMPLETE.json"]:
        shutil.copyfile(BASE / name, catalog / name)
    if not (V4 / "vendor").exists():
        shutil.copytree(
            BASE / "vendor", V4 / "vendor", ignore=shutil.ignore_patterns("__pycache__")
        )
    attempts = [
        json.loads(s)
        for s in (PUBLIC / "source_attempts.jsonl").read_text().splitlines()
    ]
    write_json(
        PUBLIC / "acquisition_lineage.json",
        dict(
            request_and_response_bytes_retained=True,
            earliest_attempts_without_per_request_capture_helper_sha256=sum(
                "capture_transform_sha256" not in r for r in attempts
            ),
            limitation="earliest v4 capture helper was not per-request hash-bound; all normalized derivatives use archived parser/bridge source and original-byte offline replay",
            normalized_derivation_source_bytes_archived=True,
        ),
    )
    write_json(
        PUBLIC / "runtime.json",
        dict(
            python=platform.python_version(),
            pandas=pd.__version__,
            pyarrow=pyarrow.__version__,
            pdf_engine="PyMuPDF 1.26.5, frozen vendor",
            baseline_v3=BASE_ID,
            raw_redistribution_authorized=False,
        ),
    )
    staging = (
        V4 / "releases" / ("staging_" + utc_now().replace(":", "").replace(".", ""))
    )
    staging.mkdir(parents=True)
    for p in sorted(V4.iterdir()):
        if p.name == "releases":
            continue
        if p.is_dir():
            shutil.copytree(
                p, staging / p.name, ignore=shutil.ignore_patterns("__pycache__")
            )
        else:
            shutil.copyfile(p, staging / p.name)
    shutil.copytree(
        PUBLIC,
        staging / "provenance",
        ignore=shutil.ignore_patterns("release.json", "frozen_code_replay.json"),
    )
    source = staging / "source"
    source.mkdir()
    for folder in ["src", "tests", "configs", "schemas"]:
        shutil.copytree(
            EP / folder, source / folder, ignore=shutil.ignore_patterns("__pycache__")
        )
    for name in [
        "GOAL.md",
        "README.md",
        "data_dictionary.md",
        "requirements.txt",
        "research_plan.md",
    ]:
        shutil.copyfile(EP / name, source / name)
    shutil.copyfile(EP / "reports/pit_v4.md", source / "pit_v4.md")
    files = [
        dict(
            relative_path=str(p.relative_to(staging)),
            bytes=p.stat().st_size,
            sha256=sha(p),
        )
        for p in sorted(staging.rglob("*"))
        if p.is_file()
    ]
    manifest = staging / "FULL_MANIFEST.json"
    write_json(manifest, files)
    release_id = sha(manifest)
    write_json(
        staging / "COMPLETE.json",
        dict(
            release_id=release_id,
            full_manifest_sha256=release_id,
            sealed_at=utc_now(),
            baseline_v3_release_id=BASE_ID,
            source_normalized_input_copies_independent=True,
            baseline_domain_extension_not_full_pit_ready=True,
        ),
    )
    target = V4 / "releases" / release_id
    staging.rename(target)
    result = verify(target)
    write_json(PUBLIC / "release.json", result)
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify-release")
    a = p.parse_args()
    if a.verify_release:
        print(json.dumps(verify(a.verify_release), ensure_ascii=False))
    else:
        seal()
