"""Independent versioned v5 snapshots and byte verification."""
import argparse
import json
import shutil

from archive import EP, sha, utc_now, write_json
from v5_core import BASE, BASE_ID, V5, PUBLIC


def verify(root):
    from pathlib import Path
    root = Path(root)
    complete = json.loads((root / "COMPLETE.json").read_text())
    assert sha(root / "FULL_MANIFEST.json") == complete["full_manifest_sha256"]
    files = json.loads((root / "FULL_MANIFEST.json").read_text())
    for r in files:
        p = root / r["relative_path"]
        assert p.stat().st_nlink == 1 and p.stat().st_size == r["bytes"] and sha(p) == r["sha256"]
    return dict(status="PASS", release_id=complete["release_id"], path=str(root),
                files_verified=len(files), bytes_verified=sum(r["bytes"] for r in files),
                independent_copies_no_hardlinks=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-release")
    args = parser.parse_args()
    if args.verify_release:
        print(json.dumps(verify(args.verify_release)))
        return
    assert json.loads((PUBLIC / "validation.json").read_text())["status"] == "PASS"
    cat = V5 / "baseline_catalog"
    cat.mkdir(exist_ok=True)
    for name in ["FULL_MANIFEST.json", "COMPLETE.json"]:
        shutil.copyfile(BASE / name, cat / name)
    stage = V5 / "releases" / ("staging_" + utc_now().replace(":", "").replace(".", ""))
    stage.mkdir(parents=True)
    for p in V5.iterdir():
        if p.name in {"releases", "replay"}:
            continue
        if p.is_dir():
            shutil.copytree(p, stage / p.name, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copyfile(p, stage / p.name)
    shutil.copytree(PUBLIC, stage / "provenance", ignore=shutil.ignore_patterns("release.json", "frozen_code_replay.json"))
    for folder in ["src", "tests", "configs", "schemas"]:
        shutil.copytree(EP / folder, stage / "source" / folder, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ["README.md", "GOAL.md", "data_dictionary.md", "requirements.txt", "research_plan.md"]:
        shutil.copyfile(EP / name, stage / "source" / name)
    shutil.copyfile(EP / "reports/pit_v5.md", stage / "source/pit_v5.md")
    files = [dict(relative_path=str(p.relative_to(stage)), bytes=p.stat().st_size, sha256=sha(p))
             for p in sorted(stage.rglob("*")) if p.is_file()]
    write_json(stage / "FULL_MANIFEST.json", files)
    release_id = sha(stage / "FULL_MANIFEST.json")
    write_json(stage / "COMPLETE.json", dict(release_id=release_id, full_manifest_sha256=release_id,
        sealed_at=utc_now(), baseline_v4_release_id=BASE_ID, quality_tier="Historical-proxy",
        policy="all requested policies are inferred qfq price changes", no_actual_execution_or_terminal_wealth_certification=True))
    target = V5 / "releases" / release_id
    stage.rename(target)
    for p in target.rglob("*"):
        if p.is_file():
            p.chmod(0o444)
    result = verify(target)
    write_json(PUBLIC / "release.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
