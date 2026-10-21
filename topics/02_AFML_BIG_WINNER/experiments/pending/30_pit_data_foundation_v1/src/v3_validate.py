"""Offline raw replay, strict-label null checks, and predecessor preservation."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
import pandas as pd
from archive import EP, CACHE, sha, write_json
from v3_core import V3, PUBLIC3, V2_RELEASE


def verified_release(root):
    complete = json.loads((root / "COMPLETE.json").read_text())
    manifest = root / "FULL_MANIFEST.json"
    if sha(manifest) != complete["full_manifest_sha256"]:
        raise ValueError("predecessor frozen manifest changed")
    records = json.loads(manifest.read_text())
    for r in records:
        if sha(root / r["relative_path"]) != r["sha256"]:
            raise ValueError("predecessor frozen bytes changed: " + r["relative_path"])
    return len(records)


def validate():
    for name in [
        "core_document_summary",
        "retirement_acquisition_summary",
        "financial_document_summary",
        "terminal_window_summary",
    ]:
        if not (PUBLIC3 / (name + ".json")).exists():
            raise ValueError("acquisition not complete: " + name)
    index_pages, quote_partitions = 0, 0
    raw_digests, transform_digests = set(), set()
    from v3_core import read_verified

    for p in sorted((V3 / "indices").glob("**/page_*.parquet")):
        f, r = read_verified(p)
        raw = json.loads(Path(r["archive_path"]).read_bytes())
        original = raw["data"]["list"]
        reconstructed = [json.loads(v) for v in f.announcement]
        if reconstructed != original:
            raise ValueError("raw disclosure index replay differs")
        raw_digests.add(r["sha256"])
        transform_digests.add(r["transform_sha256"])
        index_pages += 1
    for p in sorted((V3 / "acquired/exchange_quotes").glob("*.parquet")):
        f, r = read_verified(p)
        raw = json.loads(Path(r["archive_path"]).read_bytes())
        expected = pd.DataFrame(
            raw.get("kline") or [],
            columns=["date", "open", "high", "low", "close", "volume", "money"],
        )
        if len(expected):
            expected["date"] = pd.to_datetime(
                expected.date.astype(str), format="%Y%m%d"
            )
        pd.testing.assert_frame_equal(f, expected)
        raw_digests.add(r["sha256"])
        transform_digests.add(r["transform_sha256"])
        quote_partitions += 1
    documents, recovered, unresolved = 0, 0, []
    for p in sorted((V3 / "documents").glob("**/*.json")):
        r = json.loads(p.read_text())
        documents += 1
        if r["status"] != "ORIGINAL_PDF_RECOVERED":
            unresolved.append(
                dict(art_code=p.stem, group=p.parent.name, reason=r.get("error"))
            )
            continue
        digest = r["source"]["sha256"]
        source = Path(r["source"]["archive_path"])
        if sha(source) != digest or not source.read_bytes().startswith(b"%PDF"):
            raise ValueError("missing or altered original PDF")
        raw_digests.add(digest)
        recovered += 1
    # Each capture is the original transport response, including rejected probes.
    for line in (PUBLIC3 / "source_attempts.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r.get("sha256"):
            raw_digests.add(r["sha256"])
    for digest in raw_digests | transform_digests:
        source = CACHE / "raw/sha256" / digest[:2] / digest
        if not source.exists() or sha(source) != digest:
            raise ValueError(
                "raw or exact historical transform bytes missing: " + digest
            )
    for p in (V3 / "normalized/labels").glob("**/*.parquet"):
        f = pd.read_parquet(p)
        if (
            f.value.notna().any()
            or f.loss_below_minus20.notna().any()
            or f.mfe.notna().any()
            or f.mae.notna().any()
        ):
            raise ValueError("unverified execution created a numeric strict outcome")
        if not f.status.isin(["UNKNOWN", "CENSORED"]).all():
            raise ValueError("unexpected strict outcome status")
        if (
            f.loc[f.terminal_rights_required, "scheduled_open_price_proxy"]
            .notna()
            .any()
        ):
            raise ValueError(
                "a retained quote substituted for post-delisting terminal wealth"
            )
        if f.duplicated(["security_id", "date", "horizon", "return_policy"]).any():
            raise ValueError("duplicate strict label")
    legacy = pd.read_parquet(
        V2_RELEASE / "normalized/legacy_bridge_with_v2_quote_availability.parquet"
    )
    bridge = pd.read_parquet(V3 / "normalized/full_monthly_bridge.parquet")
    inputs = json.loads((PUBLIC3 / "full_bridge_summary.json").read_text())
    if inputs.get("inventory_sha256") != sha(
        V3 / "normalized/securities.parquet"
    ) or inputs.get("status_facts_sha256") != sha(
        V3 / "normalized/status_facts.parquet"
    ):
        raise ValueError("monthly bridge was built from stale qualification inputs")
    keys = ["security_id", "date"]
    a, b = legacy.set_index(keys), bridge.set_index(keys)
    for field in a.columns:
        pd.testing.assert_series_equal(
            a[field], b.loc[a.index, field], check_dtype=False, check_names=False
        )
    from v3_financial_review import build as review

    review()
    from v3_evidence import PARSER_VERSION
    from v3_core import documents as source_documents

    expected_core = {
        p.stem
        for p, r in source_documents("core")
        if r["status"] == "ORIGINAL_PDF_RECOVERED"
    }
    actual_core = {p.stem for p in (V3 / "parsed/core" / PARSER_VERSION).glob("*.json")}
    if expected_core != actual_core:
        raise ValueError("current parser did not process every recovered core original")
    effective_documents, effective_recovered, unresolved = 0, 0, []
    for group in ["core", "retirement", "financial"]:
        for p, r in source_documents(group):
            effective_documents += 1
            if r["status"] == "ORIGINAL_PDF_RECOVERED":
                effective_recovered += 1
            else:
                unresolved.append(
                    dict(
                        art_code=p.stem,
                        group=group,
                        primary_error=r.get("error"),
                        attachment_recovery_error=r.get("recovery_error"),
                    )
                )
    stop = json.loads((PUBLIC3 / "attachment_source_limit.json").read_text())
    for line in (PUBLIC3 / "source_attempts.jsonl").read_text().splitlines():
        r = json.loads(line)
        if stop["host"] in r["url"] and pd.Timestamp(
            r["source_observed_at"]
        ) >= pd.Timestamp(stop["recorded_at"]):
            raise ValueError(
                "detail source was requested after the explicit source stop"
            )
    ocr = json.loads((PUBLIC3 / "retirement_ocr_summary.json").read_text())
    environment = json.loads((PUBLIC3 / "ocr_environment.json").read_text())
    for model in environment["models"]:
        if sha(V3 / model["path"]) != model["sha256"]:
            raise ValueError("OCR model bytes changed")
    first_ocr = next((V3 / "ocr/retirement" / ocr["transform_sha256"]).glob("*.json"))
    sample = json.loads(first_ocr.read_text())
    import hashlib

    sys.path.insert(0, str(V3 / "vendor"))
    import pymupdf

    original = (
        CACHE / "raw/sha256" / sample["source_sha256"][:2] / sample["source_sha256"]
    )
    with pymupdf.open(original) as pdf:
        for page in sample["pages"]:
            pix = pdf[page["physical_page"] - 1].get_pixmap(
                matrix=pymupdf.Matrix(2, 2), colorspace=pymupdf.csRGB, alpha=False
            )
            if hashlib.sha256(pix.samples).hexdigest() != page["rgb_pixels_sha256"]:
                raise ValueError("OCR source raster replay changed")
    # Old experiments are preserved exactly, including their original conclusions.
    prior = json.loads((EP / "outputs/manifests/prior_preservation.json").read_text())
    repo = EP.parents[4]
    for path, digest in prior.items():
        if sha(repo / path) != digest:
            raise ValueError("protected predecessor changed: " + path)
    v1 = (
        CACHE
        / "releases/f97e739dcc7bae24ff996106343211a5d0bc05146f3d823dbefeac1d73b453b9"
    )
    # V1 uses its own frozen release format and verifier.
    execution = subprocess.run(
        [sys.executable, str(EP / "src/verify_release.py"), "--release", str(v1)],
        check=True,
        capture_output=True,
        text=True,
    )
    v1_result = json.loads(execution.stdout)
    v2_files = verified_release(V2_RELEASE)
    pd.DataFrame(unresolved).to_csv(
        PUBLIC3 / "original_document_unresolved.csv", index=False
    )
    result = dict(
        status="PASS",
        disclosure_index_pages_replayed=index_pages,
        exchange_histories_replayed=quote_partitions,
        original_document_records=documents,
        recovered_original_documents=recovered,
        effective_document_records=effective_documents,
        effective_recovered_document_records=effective_recovered,
        unresolved_current_document_records=len(unresolved),
        raw_response_digests_verified=len(raw_digests),
        exact_transform_versions_verified=len(transform_digests),
        current_core_parser_matches_all_recovered_originals=True,
        predecessor_files_preserved=len(prior),
        v1_verification=v1_result,
        v2_frozen_files_verified=v2_files,
        old_bridge_rows_and_all_columns_preserved=len(legacy),
        strict_unknowns_never_zero_filled=True,
        financial_future_revision_replay_pass=True,
        detail_source_stop_respected=True,
        ocr_model_hashes_and_sample_raster_replay=True,
    )
    write_json(PUBLIC3 / "validation.json", result)
    print(json.dumps(result, default=str), flush=True)
    return result


if __name__ == "__main__":
    argparse.ArgumentParser().parse_args()
    validate()
