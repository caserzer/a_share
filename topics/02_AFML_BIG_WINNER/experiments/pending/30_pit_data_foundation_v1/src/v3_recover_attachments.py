"""Recover endpoint-declared PDF attachments instead of assuming every route is H2."""

import argparse
import json
from urllib.parse import urlparse
from archive import write_json
from v3_core import V3, PUBLIC3, Capture, code_version, documents


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-in-progress", action="store_true")
    args = parser.parse_args()
    if not args.allow_in_progress:
        for name in [
            "core_document_summary",
            "retirement_acquisition_summary",
            "financial_document_summary",
            "terminal_window_summary",
        ]:
            if not (PUBLIC3 / (name + ".json")).exists():
                raise ValueError(
                    "finish primary acquisition before final attachment recovery"
                )
    http, results = Capture(), []
    version = code_version(__file__)
    for group in ["core", "financial", "retirement"]:
        for path, r in documents(group):
            if r["status"] == "ORIGINAL_PDF_RECOVERED":
                continue
            target = V3 / f"documents/attachment_recovery/{group}/{path.stem}.json"
            if target.exists():
                results.append(json.loads(target.read_text()))
                continue
            a = r["announcement"]
            recovered = dict(
                r,
                recovery_transform_sha256=version,
                previous_attempt_metadata=str(path),
            )
            if (V3 / "provider_gates/np-cnotice-stock.eastmoney.com.stop").exists():
                recovered.update(
                    status="UNKNOWN",
                    recovery_error="DETAIL_SOURCE_STOPPED_HTTP_567_OR_REFUSAL",
                    declared_attachment_request_attempted=False,
                )
                write_json(target, recovered)
                results.append(recovered)
                continue
            recovered["declared_attachment_request_attempted"] = True
            try:
                b, index = http.fetch(
                    "attachment_metadata_" + path.stem,
                    "https://np-cnotice-stock.eastmoney.com/api/content/ann",
                    params=dict(art_code=path.stem, client_source="web", page_index=1),
                )
                payload = json.loads(b)
                d = payload.get("data") or {}
                if (
                    payload.get("success") != 1
                    or d.get("art_code") != path.stem
                    or d.get("notice_date", "")[:10] != a["notice_date"][:10]
                ):
                    raise ValueError("attachment disclosure id or publication mismatch")
                url = d.get("attach_url_web") or d.get("attach_url")
                if (
                    not url
                    or urlparse(url).netloc != "pdf.dfcfw.com"
                    or not url.startswith("https://")
                ):
                    raise ValueError("no endpoint-declared public PDF attachment")
                body, source = http.fetch("declared_attachment_" + path.stem, url)
                if not body.startswith(b"%PDF"):
                    raise ValueError("declared attachment is not PDF")
                recovered.update(
                    status="ORIGINAL_PDF_RECOVERED",
                    source=source,
                    attachment_metadata_source=index,
                    attachment_route=url,
                    source_class="PUBLISHER_DISCLOSURE_MIRROR_ATTACHMENT_NOT_INTRADAY_ARCHIVE",
                    historical_first_version_certified=False,
                    error=None,
                )
            except PermissionError:
                raise
            except Exception as exc:
                recovered.update(status="UNKNOWN", recovery_error=str(exc)[:250])
            write_json(target, recovered)
            results.append(recovered)
            print(
                "declared attachment", group, path.stem, recovered["status"], flush=True
            )
    results = [
        json.loads(p.read_text())
        for p in (V3 / "documents/attachment_recovery").glob("*/*.json")
    ]
    write_json(
        PUBLIC3 / "attachment_recovery_summary.json",
        dict(
            attempted=len(results),
            recovered=sum(r["status"] == "ORIGINAL_PDF_RECOVERED" for r in results),
            unresolved=sum(r["status"] != "ORIGINAL_PDF_RECOVERED" for r in results),
            actual_requests_attempted=sum(
                r.get("declared_attachment_request_attempted", True) for r in results
            ),
            skipped_after_source_stop=sum(
                not r.get("declared_attachment_request_attempted", True)
                for r in results
            ),
            all_primary_acquisitions_complete=not args.allow_in_progress,
            transform_sha256=version,
        ),
    )


if __name__ == "__main__":
    main()
