"""Original bytes, alias boundaries, full labels and preserved legacy inputs."""

import json
from pathlib import Path

import pandas as pd

from archive import EP, sha, write_json
from v4_core import BASE, PUBLIC, V4


def validate(root=V4, preserve=True):
    root = Path(root)
    inputs = {
        r["relative_path"]: r
        for r in [
            json.loads(s)
            for s in (root / "input_manifest.jsonl").read_text().splitlines()
        ]
    }
    for name, r in inputs.items():
        if sha(root / "inputs" / name) != r["sha256"]:
            raise ValueError("changed baseline input: " + name)
    inv = pd.read_parquet(root / "normalized/securities.parquet")
    redirects = pd.read_parquet(root / "normalized/security_id_redirects.parquet")
    deprecated = set(redirects.legacy_security_id)
    assert len(inv) == 5919 and not inv.security_id.isin(deprecated).any()
    assert inv.security_id.nunique() == len(inv)
    for r in redirects.itertuples():
        row = inv[inv.security_id.eq(r.canonical_security_id)].iloc[0]
        assert pd.isna(row.delist_date) and not row.is_delisted
        f = pd.read_parquet(
            root / f"normalized/prices/{r.canonical_security_id}.parquet"
        )
        assert not f.date.duplicated().any()
        assert (
            f.loc[f.date.lt(r.effective_date), "code_interval_source_instrument"]
            .eq(r.old_instrument)
            .all()
        )
        assert (
            f.loc[f.date.ge(r.effective_date), "code_interval_source_instrument"]
            .eq(r.new_instrument)
            .all()
        )
        assert not f.can_buy.notna().any() and not f.can_sell.notna().any()
    summary = (
        json.loads((root / "provenance/full_bridge_summary.json").read_text())
        if (root / "provenance/full_bridge_summary.json").exists()
        else json.loads((PUBLIC / "full_bridge_summary.json").read_text())
    )
    assert sha(root / "normalized/securities.parquet") == summary["inventory_sha256"]
    assert (
        sha(root / "normalized/status_facts.parquet") == summary["status_facts_sha256"]
    )
    n, counts = 0, []
    for artifact in summary["labels"]:
        p = root / artifact["path"]
        assert sha(p) == artifact["sha256"]
        f = pd.read_parquet(p)
        n += len(f)
        assert not f.security_id.isin(deprecated).any()
        assert not f.duplicated(["security_id", "date"]).any()
        assert f[["value", "loss_below_minus20", "mfe", "mae"]].isna().all().all()
        assert f.status.isin(["UNKNOWN", "CENSORED"]).all()
        assert f.loc[f.target_session.isna(), "status"].eq("CENSORED").all()
        assert not f.strict_entry_execution_known.any()
        out = f.security_id.map(inv.set_index("security_id").delist_date)
        invalid = out.notna() & (
            (f.scheduled_entry_session_diagnostic >= out) | (f.target_session >= out)
        )
        assert f.loc[invalid, "scheduled_open_price_proxy"].isna().all()
        for r in redirects.itertuples():
            g = f[f.security_id.eq(r.canonical_security_id)]
            assert (
                g.loc[g.date.lt(r.effective_date), "instrument"]
                .eq(r.old_instrument)
                .all()
            )
            assert (
                g.loc[g.date.ge(r.effective_date), "instrument"]
                .eq(r.new_instrument)
                .all()
            )
        counts.append(dict(path=artifact["path"], rows=len(f), known=0))
    assert n == 6309144
    old = pd.read_parquet(
        root
        / "inputs/baseline/normalized/legacy_bridge_with_v2_quote_availability.parquet"
    )
    bridge = pd.read_parquet(root / "normalized/full_monthly_bridge.parquet")
    keys = ["date", "security_id"]
    before = old.set_index(keys)
    after = bridge.set_index(keys).loc[before.index]
    pd.testing.assert_frame_equal(before, after[list(before)], check_dtype=False)
    members = bridge[bridge.v4_provisional_member]
    assert len(members) == 525762
    assert not members.duplicated(["date", "v4_canonical_security_id"]).any()
    assert not bridge.loc[
        bridge.v4_retained_legacy_alias_row, "v4_provisional_member"
    ].any()
    documents = 0
    for p in (root / "documents").rglob("*.json"):
        r = json.loads(p.read_text())
        if r.get("status") != "ORIGINAL_PDF_RECOVERED":
            continue
        s = r["source"]
        h = s["sha256"]
        raw = root / "raw/sha256" / h[:2] / h
        assert sha(raw) == h and raw.read_bytes().startswith(b"%PDF")
        documents += 1
    indices = 0
    for p in (root / "cninfo").rglob("*.json"):
        r = json.loads(p.read_text())
        if not isinstance(r, dict) or not r.get("complete"):
            continue
        rows = []
        for s in r["sources"]:
            h = s["sha256"]
            raw = root / "raw/sha256" / h[:2] / h
            assert sha(raw) == h
            payload = json.loads(raw.read_bytes())
            assert payload["totalAnnouncement"] == r["reported_total"]
            rows.extend(payload.get("announcements") or [])
        assert len(rows) == len(r["announcements"]) == r["reported_total"]
        assert [a["announcementId"] for a in rows] == [
            a["announcementId"] for a in r["announcements"]
        ]
        assert len(set(a["announcementId"] for a in rows)) == len(rows)
        indices += 1
    receipts = root / "provenance/source_attempts.jsonl"
    if not receipts.exists():
        receipts = PUBLIC / "source_attempts.jsonl"
    attempts = [json.loads(s) for s in receipts.read_text().splitlines()]
    for s in attempts:
        assert (
            "np-cnotice-stock.eastmoney.com" not in s["url"]
            and "www.neeq.com.cn" not in s["url"]
        )
        if "sha256" in s:
            h = s["sha256"]
            assert sha(root / "raw/sha256" / h[:2] / h) == h
    # Review images must be actual raster pixels of the archived originals.
    import sys

    vendor = root / "vendor" if (root / "vendor").exists() else BASE / "vendor"
    sys.path.insert(0, str(vendor))
    import pymupdf
    from PIL import Image

    images = 0
    source_config = (
        root / "source/configs"
        if (root / "source/configs").exists()
        else EP / "configs"
    )
    for name in [
        "v4_identity_page_reviews.json",
        "v4_source_page_reviews.json",
        "v4_code_change_page_reviews.json",
    ]:
        for review in json.loads((source_config / name).read_text()):
            h = review["source_sha256"]
            raw = root / "raw/sha256" / h[:2] / h
            with pymupdf.open(raw) as pdf:
                for im in review["images"]:
                    rel = im.get("path", im.get("full_image"))
                    digest = im.get("sha256", im.get("full_image_sha256"))
                    p = root / rel
                    assert sha(p) == digest
                    with Image.open(p) as image:
                        # Financial and code-change reviews: 108 dpi; scanned confirmations: 144 dpi.
                        scale = (
                            2
                            if name == "v4_identity_page_reviews.json"
                            or (
                                name == "v4_source_page_reviews.json"
                                and "identity/" in rel
                            )
                            else 1.5
                        )
                        pix = pdf[im["physical_page"] - 1].get_pixmap(
                            matrix=pymupdf.Matrix(scale, scale),
                            colorspace=pymupdf.csRGB,
                            alpha=False,
                        )
                        assert image.convert("RGB").tobytes() == pix.samples
                    images += 1
    protected = baseline_files = 0
    if preserve:
        for name, digest in json.loads(
            (EP / "outputs/manifests/prior_preservation.json").read_text()
        ).items():
            assert sha(Path.cwd() / name) == digest
            protected += 1
        full = json.loads((BASE / "FULL_MANIFEST.json").read_text())
        for i, r in enumerate(full):
            assert sha(BASE / r["relative_path"]) == r["sha256"]
            baseline_files += 1
            if i and i % 20000 == 0:
                print("v3 preserved files", i, flush=True)
    return dict(
        status="PASS",
        verified_baseline_inputs=len(inputs),
        original_document_records=documents,
        complete_cninfo_indices_replayed=indices,
        source_attempts_verified=len(attempts),
        original_pixel_pages_replayed=images,
        strict_labels=n,
        strict_known=0,
        canonical_member_months=len(members),
        legacy_rows_preserved=len(old),
        protected_prior_files_verified=protected,
        immutable_v3_files_verified=baseline_files,
        code_changes_do_not_imply_open_fill=True,
        unknown_terminal_wealth_not_zero=True,
        labels=counts,
    )


if __name__ == "__main__":
    write_json(PUBLIC / "validation.json", validate())
