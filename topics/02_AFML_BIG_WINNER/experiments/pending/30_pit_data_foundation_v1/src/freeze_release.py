"""Freeze a private, independently copied D2 release and public hash receipt."""

import json
from pathlib import Path
import shutil
import pandas as pd
from archive import EP, CACHE, sha, write_json


def main():
    m = EP / "outputs/manifests"
    # Include public result hashes, schemas and exact code/config, excluding self-reference.
    public = []
    for root in [
        EP / "src",
        EP / "tests",
        EP / "configs",
        EP / "schemas",
        EP / "reports",
        EP / "outputs/audits",
    ]:
        for p in sorted(root.rglob("*")):
            if (
                p.is_file()
                and "__pycache__" not in p.parts
                and p.suffix not in [".pyc", ".log"]
            ):
                public.append(
                    dict(
                        path=str(p.relative_to(EP)),
                        sha256=sha(p),
                        bytes=p.stat().st_size,
                    )
                )
    for p in [
        EP / "GOAL.md",
        EP / "README.md",
        EP / "research_plan.md",
        EP / "data_dictionary.md",
        EP / "requirements.txt",
    ]:
        public.append(
            dict(path=str(p.relative_to(EP)), sha256=sha(p), bytes=p.stat().st_size)
        )
    for p in sorted(m.glob("*")):
        if p.name not in ["delivery_manifest.json", "release.json"]:
            public.append(
                dict(path=str(p.relative_to(EP)), sha256=sha(p), bytes=p.stat().st_size)
            )
    public.sort(key=lambda r: r["path"])
    write_json(m / "delivery_manifest.json", dict(version="D2-v1", files=public))
    release_id = sha(m / "delivery_manifest.json")
    target = CACHE / "releases" / release_id
    products = pd.read_csv(m / "local_cache_manifest.csv")
    if target.exists():
        if not (target / "COMPLETE.json").exists():
            raise ValueError("incomplete release directory: inspect before reuse")
        for r in products.itertuples():
            if sha(target / r.relative_path) != r.sha256:
                raise ValueError("existing release changed")
    else:
        target.mkdir(parents=True)
        for r in products.itertuples():
            dst = target / r.relative_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(r.path, dst)
            if sha(dst) != r.sha256:
                raise ValueError("release copy mismatch")
            # Independent copy: later working-cache rewrites cannot alter this snapshot.
            dst.chmod(0o400)
            sidecar = Path(str(r.path) + ".manifest.json")
            if sidecar.exists():
                shutil.copyfile(sidecar, str(dst) + ".manifest.json")
        # Keep exact auditable code and receipts beside the frozen data.
        for directory in [
            "src",
            "configs",
            "schemas",
            "reports",
            "outputs/audits",
            "outputs/manifests",
        ]:
            shutil.copytree(
                EP / directory,
                target / "provenance" / directory,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "release.json"),
            )
        shutil.copytree(
            EP / "tests",
            target / "provenance/tests",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "release.json"),
        )
        for name in [
            "GOAL.md",
            "README.md",
            "research_plan.md",
            "data_dictionary.md",
            "requirements.txt",
        ]:
            shutil.copyfile(EP / name, target / "provenance" / name)
        for line in (
            (EP / "outputs/audits/source_attempts.jsonl").read_text().splitlines()
        ):
            r = json.loads(line)
            if r.get("sha256"):
                dst = target / "raw/sha256" / r["sha256"][:2] / r["sha256"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists():
                    shutil.copyfile(r["archive_path"], dst)
                assert sha(dst) == r["sha256"]
                dst.chmod(0o400)
        write_json(
            target / "COMPLETE.json",
            dict(
                release_id=release_id,
                products=len(products),
                public_delivery_sha256=release_id,
                format="independent_copy_not_hardlink",
                all_product_hashes_verified=True,
            ),
        )
    write_json(
        m / "release.json",
        dict(
            release_id=release_id,
            private_path=str(target),
            products=len(products),
            replay="verify_release.py --release " + str(target),
            public_delivery_sha256=release_id,
        ),
    )
    print(
        "immutable private D2 release",
        release_id,
        "products",
        len(products),
        flush=True,
    )


if __name__ == "__main__":
    main()
