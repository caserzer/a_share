"""Read-only, exact-release adapter. No network and no label-to-feature joins."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

from common import EXPECTED_RELEASE, OUT, PREDECESSOR, cache, sha, utc_now, write_json


class EP30Adapter:
    def __init__(self):
        pointer = json.loads((PREDECESSOR / "outputs/pit_v5/release.json").read_text())
        if pointer["release_id"] != EXPECTED_RELEASE:
            raise ValueError("EP31 is pinned to D2-v5; silent release switching forbidden")
        self.root = Path(pointer["path"])
        complete = json.loads((self.root / "COMPLETE.json").read_text())
        if complete["release_id"] != EXPECTED_RELEASE or sha(self.root / "FULL_MANIFEST.json") != EXPECTED_RELEASE:
            raise ValueError("EP30 seal mismatch")
        self.files = {r["relative_path"]: r for r in json.loads((self.root / "FULL_MANIFEST.json").read_text())}
        # Use the required verified EP30 public reader without altering it.
        sys.path.insert(0, str(PREDECESSOR / "src"))
        from v5_dataset import D2PriceInferenceDataset
        self.dataset = D2PriceInferenceDataset(self.root)
        self.inventory = self.dataset.inventory.copy()
        self.days = pd.DatetimeIndex(self.read("inputs/inputs/baseline/normalized/calendar.parquet").date)
        self.checked = set()

    def path(self, relative):
        p = self.root / relative
        if relative not in self.files or not p.is_file() or sha(p) != self.files[relative]["sha256"]:
            raise ValueError("changed sealed input: " + relative)
        return p

    def read(self, relative):
        return pd.read_parquet(self.path(relative))

    def bars(self, sid):
        name = f"normalized/prices_qfq/{sid}.parquet"
        if name not in self.files:
            return None
        return self.read(name)

    def verify_all(self):
        total = 0
        for i, (name, r) in enumerate(self.files.items()):
            p = self.path(name)
            if p.stat().st_size != r["bytes"]:
                raise ValueError("changed byte count: " + name)
            total += r["bytes"]
            if i % 5000 == 0:
                print("verify EP30", i, "/", len(self.files), flush=True)
        receipt = dict(status="PASS", checked_at=utc_now(), release_id=EXPECTED_RELEASE,
                       files_verified=len(self.files), bytes_verified=total, read_only=True,
                       private_release=str(self.root), full_manifest_sha256=sha(self.root / "FULL_MANIFEST.json"))
        write_json(OUT / "audits/ep30_release_verification.json", receipt)
        return receipt


def h09_gate(columns, timestamp_attested=False):
    required = {"trade_count", "trade_size", "known_at", "trade_category"}
    return "ELIGIBLE" if required.issubset(columns) and timestamp_attested else "BLOCKED_DATA"
