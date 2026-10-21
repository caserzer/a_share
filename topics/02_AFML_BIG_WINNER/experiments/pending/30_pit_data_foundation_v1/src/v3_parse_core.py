"""Incremental parsing of archived core originals; emits no positive fill assumptions."""

import argparse
import json
import time
import pandas as pd
from archive import write_json
from v3_core import V3, PUBLIC3, documents
from v3_evidence import parse_document, security_map, calendar
from pit import COLUMNS, FactStore


def parse_available():
    from v3_evidence import PARSER_VERSION

    version = PARSER_VERSION
    mapping = security_map()
    output = V3 / "parsed/core" / version
    output.mkdir(parents=True, exist_ok=True)
    for p, r in documents("core"):
        target = output / p.name
        if target.exists():
            continue
        if r["status"] != "ORIGINAL_PDF_RECOVERED":
            continue
        try:
            result = parse_document(r, mapping)
            result["parse_status"] = (
                "PARSED"
                if result["extractable_text_characters"]
                else "SOURCE_TEXT_UNAVAILABLE"
            )
        except Exception as exc:
            result = dict(art_code=p.stem, parse_status="UNKNOWN", error=str(exc)[:250])
        write_json(target, result)
    return output


def aggregate(output):
    facts, schedules, amounts, retirements, docs = [], [], [], [], []
    cal = calendar()
    for p in sorted(output.glob("*.json")):
        r = json.loads(p.read_text())
        if r["parse_status"] != "PARSED":
            docs.append(
                dict(
                    art_code=p.stem,
                    parse_status=r["parse_status"],
                    error=r.get("error"),
                )
            )
            continue
        docs.append(
            dict(
                art_code=p.stem,
                parse_status="PARSED",
                security_id=r["security_id"],
                evidence_kind=r["evidence_kind"],
                source_sha256=r["original_source_sha256"],
                extracted_state_values=len(r["states"]),
                extracted_contract_dates=len(r["distribution_contract_dates"]),
            )
        )
        for event in r["states"]:
            known = cal.publication_time(r["notice_date"])
            if pd.isna(known):
                continue
            f = dict.fromkeys(COLUMNS)
            logical = (
                r["security_id"] + "/" + event["field"] + "/" + event["effective_date"]
            )
            f.update(
                record_id=p.stem + "/" + event["field"],
                logical_key=logical,
                security_id=r["security_id"],
                field=event["field"],
                value=event["value"],
                event_time=event["effective_date"],
                effective_time=event["effective_date"],
                known_at=known,
                source_observed_at=r["source"]["source_observed_at"],
                ingested_at=r["source"]["ingested_at"],
                source_uri=r["source"]["url"],
                source_path=r["source"]["archive_path"],
                source_sha256=r["original_source_sha256"],
                unit="boolean",
                original_version=p.stem,
                transform_sha256=r["transform_sha256"],
                quality_tier="PIT-reconstructed",
                publication_evidence=json.dumps(
                    dict(
                        index_sha256=r["index_sha256"],
                        notice_date=r["notice_date"],
                        physical_page=event["physical_page"],
                    )
                ),
                reconstruction=event["evidence_type"] + ": " + event["exact_clause"],
                supersedes=None,
            )
            facts.append(f)
        for event in r["distribution_contract_dates"]:
            schedules.append(
                dict(
                    **event,
                    security_id=r["security_id"],
                    art_code=r["art_code"],
                    notice_date=r["notice_date"],
                    source_sha256=r["original_source_sha256"],
                    source_uri=r["source"]["url"],
                    actual_payment_confirmed=False,
                )
            )
        for event in r.get("distribution_contract_amounts", []):
            amounts.append(
                dict(
                    **event,
                    security_id=r["security_id"],
                    art_code=r["art_code"],
                    notice_date=r["notice_date"],
                    source_sha256=r["original_source_sha256"],
                    source_uri=r["source"]["url"],
                    actual_payment_confirmed=False,
                )
            )
        for event in r["retirement_codes"]:
            retirements.append(
                dict(
                    **event,
                    security_id=r["security_id"],
                    art_code=r["art_code"],
                    notice_date=r["notice_date"],
                    source_sha256=r["original_source_sha256"],
                    source_uri=r["source"]["url"],
                )
            )
    store = FactStore(facts)
    store.to_parquet(V3 / "normalized/status_facts.parquet")
    pd.DataFrame(docs).to_csv(PUBLIC3 / "core_document_parsing.csv", index=False)
    if facts:
        pd.DataFrame(facts).drop(columns=["source_path"]).to_csv(
            PUBLIC3 / "reconstructed_status_facts.csv", index=False
        )
    pd.DataFrame(schedules).to_parquet(
        V3 / "normalized/distribution_contract_dates.parquet", index=False
    )
    pd.DataFrame(schedules).to_csv(
        PUBLIC3 / "distribution_contract_dates.csv", index=False
    )
    pd.DataFrame(amounts).to_parquet(
        V3 / "normalized/distribution_contract_amounts.parquet", index=False
    )
    pd.DataFrame(amounts).drop(columns=["exact_clause"], errors="ignore").to_csv(
        PUBLIC3 / "distribution_contract_amounts.csv", index=False
    )
    pd.DataFrame(retirements).to_parquet(
        V3 / "normalized/retirement_code_evidence.parquet", index=False
    )
    pd.DataFrame(retirements).to_csv(
        PUBLIC3 / "retirement_code_evidence.csv", index=False
    )
    write_json(
        PUBLIC3 / "core_reconstruction_summary.json",
        dict(
            parsed_documents=len(docs),
            reconstructed_state_facts=len(facts),
            document_parse_status_counts=pd.DataFrame(docs)
            .parse_status.value_counts()
            .to_dict(),
            securities_with_state_facts=len(set(f["security_id"] for f in facts)),
            contract_date_values=len(schedules),
            contract_amount_values=len(amounts),
            actual_cash_receipts_confirmed=0,
            retirement_board_code_assertions=len(retirements),
            independent_human_review=False,
            positive_open_fill_flags_created=0,
            full_status_and_rights_coverage_attested=False,
            canonical_parser_generation=output.name,
            older_parser_generations_are_diagnostics_only=True,
        ),
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--watch", action="store_true")
    args = p.parse_args()
    while True:
        output = parse_available()
        aggregate(output)
        if not args.watch or (PUBLIC3 / "core_document_summary.json").exists():
            break
        print("parsed originals", len(list(output.glob("*.json"))), flush=True)
        time.sleep(15)


if __name__ == "__main__":
    main()
