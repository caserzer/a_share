"""Independent immutable v3 release, including exact v2 baseline and own raw bytes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from archive import EP, CACHE, sha, write_json, utc_now, archive_bytes
from v3_core import V3, PUBLIC3, V2_RELEASE


def file_records(folder):
    return [
        dict(
            relative_path=str(p.relative_to(folder)),
            sha256=sha(p),
            bytes=p.stat().st_size,
        )
        for p in sorted(folder.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    ]


def verify(root):
    root = Path(root)
    complete = json.loads((root / "COMPLETE.json").read_text())
    if sha(root / "FULL_MANIFEST.json") != complete["full_manifest_sha256"]:
        raise ValueError("changed immutable v3 manifest")
    files = json.loads((root / "FULL_MANIFEST.json").read_text())
    for r in files:
        path = root / r["relative_path"]
        if not path.exists() or sha(path) != r["sha256"] or path.stat().st_nlink != 1:
            raise ValueError(
                "altered or hardlinked immutable v3 file: " + r["relative_path"]
            )
    from v3_dataset import D2V3Dataset

    d = D2V3Dataset(root)
    assert d.get_asof("SH600000", "close", "2026-10-21 15:00").value is None
    assert (
        d.get_asof("SH600000", "close", "2026-10-21 15:00", "Historical-proxy").value
        == 9.66
    )
    assert (
        d.get_asof(
            "SH600000", "close", "2017-01-26 15:00", "Historical-proxy", "archived"
        ).value
        is None
    )
    field = "financial:reviewed_reported_operating_cash_flow:2020-12-31"
    assert d.get_asof("BJ920132", field, "2021-04-20 15:00").value is None
    assert d.get_asof("BJ920132", field, "2021-04-21 09:30").value == 4456443.98
    assert d.get_asof("BJ920132", field, "2023-04-04 15:00").value == 4456443.98
    assert d.get_asof("BJ920132", field, "2023-04-06 09:30").value == -4549865.76
    assert (
        d.get_asof("BJ920132", field, "2023-04-06 09:30", mode="archived").value is None
    )
    assert d.get_asof("SZ000748", "can_buy", "2017-01-03 15:00").value is False
    assert d.universe_asof("2026-10-21 15:00").empty
    p = d.universe_asof("2026-10-21 15:00", "Historical-proxy")
    assert "SH600193" not in set(p.instrument)
    assert d.get_asof("SH600193", "listed", "2026-07-06 15:00").value is False
    assert d.universe_asof("2017-01-26 15:00", "Historical-proxy", "archived").empty
    label = d.build_labels("SH600000", "2020-01-23 15:00", 20, "total")
    assert label["status"] == "UNKNOWN" and pd_is_missing(label["value"])
    censored = d.build_labels(
        "SH600000", "2026-09-30 15:00", "6_calendar_months", "total"
    )
    assert censored["status"] == "CENSORED" and pd_is_missing(censored["value"])
    return dict(
        status="PASS",
        release_id=complete["release_id"],
        files_verified=len(files),
        bytes_verified=sum(r["bytes"] for r in files),
        independent_copies_no_hardlinks=True,
        offline_v3_asof_and_financial_revision_replay=True,
        strict_unknown_labels_preserved=True,
    )


def pd_is_missing(value):
    import pandas as pd

    return value is None or bool(pd.isna(value))


def freeze():
    validation = json.loads((PUBLIC3 / "validation.json").read_text())
    if validation["status"] != "PASS":
        raise ValueError("offline validation must pass before freezing")
    sources = []
    for folder in ["src", "configs", "tests", "schemas"]:
        for p in sorted((EP / folder).rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                archive_bytes(p.read_bytes())
                sources.append(
                    dict(relative_path=str(p.relative_to(EP)), sha256=sha(p))
                )
    for name in [
        "requirements.txt",
        "GOAL.md",
        "README.md",
        "data_dictionary.md",
        "research_plan.md",
    ]:
        archive_bytes((EP / name).read_bytes())
        sources.append(dict(relative_path=name, sha256=sha(EP / name)))
    seal = dict(
        sealed_at=utc_now(),
        source_files=sources,
        normalized_files=file_records(V3 / "normalized"),
        baseline_v2_id=V2_RELEASE.name,
        full_pit_ready=False,
    )
    release_id = hashlib.sha256(json.dumps(seal, sort_keys=True).encode()).hexdigest()
    release = V3 / "releases" / release_id
    staging = release.with_name(release.name + ".incomplete")
    staging.mkdir(parents=True)
    shutil.copytree(V2_RELEASE, staging / "baseline")
    for folder in [
        "normalized",
        "acquired",
        "indices",
        "documents",
        "parsed",
        "text",
        "reviews",
        "reviewed",
        "packages",
        "vendor",
        "ocr_vendor",
        "ocr",
        "probes",
        "failed_writes",
    ]:
        path = V3 / folder
        if path.exists():
            shutil.copytree(
                path,
                staging / folder,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
    # Include all actual v3 transport responses and historical transformation bytes.
    digests = set()
    for line in (PUBLIC3 / "source_attempts.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r.get("sha256"):
            digests.add(r["sha256"])
    for p in V3.rglob("*.json"):
        if "releases" in p.relative_to(V3).parts or p.parts[-2] == "text":
            continue
        try:
            value = json.loads(p.read_text())
        except (ValueError, UnicodeDecodeError):
            continue
        if isinstance(value, dict):
            for field in [
                "transform_sha256",
                "source_sha256",
                "original_source_sha256",
                "index_sha256",
            ]:
                if value.get(field):
                    digests.add(value[field])
    digests.update(r["sha256"] for r in sources)
    # Preserve older imported helper/capture modules as well as receipt-linked
    # entry points. These bytes were archived at import/capture time in v3.
    for archived in (CACHE / "raw/sha256").glob("*/*"):
        if archived.stat().st_size > 150000:
            continue
        with archived.open("rb") as handle:
            first = handle.read(3)
            if first != b'"""':
                continue
            body = first + handle.read()
        if b"v3_" in body or b"pit_v3" in body:
            digests.add(archived.name)
    for p in (V3 / "text").glob("*.json"):
        r = json.loads(p.read_text())
        digests.update([r["source_sha256"], r["transform_sha256"]])
    for digest in sorted(digests):
        original = CACHE / "raw/sha256" / digest[:2] / digest
        if not original.exists() or sha(original) != digest:
            raise ValueError(
                "missing exact source/transform bytes before freeze: " + digest
            )
        dst = staging / "raw/sha256" / digest[:2] / digest
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, dst)
    for r in sources:
        dst = staging / "source" / r["relative_path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(EP / r["relative_path"], dst)
    shutil.copytree(PUBLIC3, staging / "provenance")
    shutil.copytree(EP / "reports", staging / "provenance/reports")
    write_json(staging / "provenance/seal.json", seal)
    records = file_records(staging)
    write_json(staging / "FULL_MANIFEST.json", records)
    write_json(
        staging / "COMPLETE.json",
        dict(
            release_id=release_id,
            sealed_at=seal["sealed_at"],
            full_manifest_sha256=sha(staging / "FULL_MANIFEST.json"),
        ),
    )
    for p in staging.rglob("*"):
        if p.is_file():
            os.chmod(p, 0o444)
    staging.rename(release)
    result = verify(release)
    write_json(PUBLIC3 / "release.json", dict(path=str(release), **result))
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(args.verify)), flush=True)
    else:
        freeze()
