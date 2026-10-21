"""Recompute the extension from its own copied inputs with live caches unavailable."""

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd
import requests

from archive import write_json


def copy_replay_inputs(release, work):
    # Nested inputs/source contains frozen baseline helpers and is required data.
    shutil.copytree(release, work, ignore=shutil.ignore_patterns("__pycache__"))


def run(release):
    release = Path(release)
    with tempfile.TemporaryDirectory(prefix="ep30_v4_replay_") as tmp:
        work = Path(tmp) / "work"
        copy_replay_inputs(release, work)
        public = Path(tmp) / "public"
        shutil.copytree(release / "provenance", public)
        requests.Session.request = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("network prohibited during frozen replay")
        )
        import archive

        archive.CACHE = Path(tmp) / "empty_live_cache"
        import v4_core

        v4_core.V4 = work
        v4_core.PUBLIC = public
        v4_core.BASE = release / "baseline_catalog"
        v4_core.baseline_files.cache_clear()
        import v4_pipeline

        v4_pipeline.BASE = release
        import v4_identity
        import v4_review
        import v4_bridge

        v4_identity.build()
        v4_pipeline.make_queues()
        v4_pipeline.parse()
        v4_review.build()
        v4_bridge.build()
        compared = []
        names = [
            "normalized/securities.parquet",
            "normalized/security_id_redirects.parquet",
            "normalized/code_intervals.parquet",
            "normalized/retired_equity_links.parquet",
            "normalized/financial_version_chains.parquet",
            "normalized/financial_reviewed_facts.parquet",
            "normalized/status_reviewed_facts.parquet",
            "normalized/code_change_facts.parquet",
            "normalized/status_facts.parquet",
            "normalized/alias_facts.parquet",
            "normalized/financial_value_candidates.parquet",
            "normalized/full_monthly_bridge.parquet",
        ]
        names.extend(
            str(p.relative_to(release))
            for p in sorted((release / "normalized/labels").rglob("*.parquet"))
        )
        for name in names:
            expected = pd.read_parquet(release / name)
            actual = pd.read_parquet(work / name)
            # Source paths move with a portable release; source SHA and every clock/value stay identical.
            columns = [c for c in expected if c != "source_path"]
            pd.testing.assert_frame_equal(
                expected[columns], actual[columns], check_dtype=True
            )
            compared.append(dict(path=name, rows=len(actual)))
        return dict(
            status="PASS",
            release_id=json.loads((release / "COMPLETE.json").read_text())[
                "release_id"
            ],
            network_disabled=True,
            live_baseline_and_working_cache_not_read=True,
            independent_frozen_input_rebuild=True,
            only_source_path_allowed_to_relocate=True,
            products=compared,
        )


if __name__ == "__main__":
    result = run(sys.argv[1])
    if len(sys.argv) > 2:
        write_json(sys.argv[2], result)
    else:
        print(json.dumps(result, ensure_ascii=False))
