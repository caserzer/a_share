"""Original-source equity continuity and independent contractual/settled ledgers."""

import json
import re
from fractions import Fraction
import pandas as pd
from archive import write_json
from v3_core import V3, PUBLIC3, V2_RELEASE, inventory, code_version, documents
from v3_evidence import original_pages, compact, security_map


def ledger_value(initial_shares, entry_date, events, marks, policy, cost_cny=None):
    """Evaluate a supplied, fully attested account ledger; never assume delivery.

    Decimal ratios stay rational. Account-dependent fractional allocations must be
    explicitly supplied. Cash schedules and optional rights are not settlements.
    This evaluator does not itself attest that the caller supplied every event.
    """
    if policy not in ["total", "executable"]:
        raise ValueError("unknown rights policy")
    held = {"initial": Fraction(str(initial_shares))}
    cash, receivable = Fraction(0), Fraction(0)
    timeline = [(pd.Timestamp(entry_date), dict(held))]
    for e in sorted(events, key=lambda x: (x["effective_date"], x["event_id"])):
        if not e.get("verified") or not e.get("source_sha256"):
            return dict(status="UNKNOWN", reason="UNVERIFIED_EQUITY_EVENT", value=None)
        date = pd.Timestamp(e["effective_date"])
        record = pd.Timestamp(e["record_date"]) if e.get("record_date") else pd.NaT
        if pd.isna(record):
            return dict(status="UNKNOWN", reason="MISSING_ENTITLEMENT_DATE", value=None)
        if record < pd.Timestamp(entry_date):
            continue
        history = [h for d, h in timeline if d <= record]
        eligible = history[-1].get(e.get("instrument", "initial"), Fraction(0))
        if e["kind"] == "cash_dividend":
            amount = eligible * Fraction(str(e["cash_per_share"]))
            if e.get("actual_payment_confirmed"):
                cash += amount
            elif policy == "total":
                receivable += amount
            else:
                return dict(
                    status="UNKNOWN",
                    reason="ACTUAL_CASH_RECEIPT_NOT_CONFIRMED",
                    value=None,
                )
        elif e["kind"] == "share_exchange":
            ratio = Fraction(str(e["new_shares_per_old_share"]))
            new = eligible * ratio
            if new.denominator != 1 and not e.get("fractional_allocation_confirmed"):
                return dict(
                    status="UNKNOWN",
                    reason="ACCOUNT_FRACTIONAL_SHARE_ALLOCATION_UNKNOWN",
                    value=None,
                )
            if not e.get("actual_delivery_confirmed"):
                return dict(
                    status="UNKNOWN",
                    reason="ACTUAL_SUCCESSOR_SHARE_DELIVERY_UNKNOWN",
                    value=None,
                )
            old = e.get("instrument", "initial")
            held[old] = held.get(old, Fraction(0)) - eligible
            successor = e["successor_instrument"]
            held[successor] = held.get(successor, Fraction(0)) + new
        elif e["kind"] == "rights_issue":
            return dict(
                status="UNKNOWN",
                reason="OPTIONAL_SUBSCRIPTION_AND_SETTLEMENT_NOT_VERIFIED",
                value=None,
            )
        elif e["kind"] == "legal_cancellation":
            if not e.get("final_entitlement_and_settlement_confirmed"):
                return dict(
                    status="UNKNOWN",
                    reason="LEGAL_CANCELLATION_DOES_NOT_PROVE_NO_CASH_CLAIM",
                    value=None,
                )
            held[e.get("instrument", "initial")] = Fraction(0)
            cash += Fraction(str(e["final_cash_per_share"])) * eligible
        else:
            return dict(status="UNKNOWN", reason="UNSUPPORTED_EQUITY_EVENT", value=None)
        timeline.append((date, dict(held)))
    total = cash + receivable
    for instrument, shares in held.items():
        if not shares:
            continue
        if instrument not in marks or marks[instrument] is None:
            return dict(
                status="UNKNOWN", reason="MISSING_TERMINAL_EQUITY_MARK", value=None
            )
        total += shares * Fraction(str(marks[instrument]))
    if policy == "executable":
        if cost_cny is None:
            return dict(
                status="UNKNOWN",
                reason="EXECUTION_COST_POLICY_NOT_SPECIFIED",
                value=None,
            )
        total -= Fraction(str(cost_cny))
    return dict(
        status="KNOWN_ON_SUPPLIED_LEDGER_ONLY",
        value=float(total),
        cash=float(cash),
        receivable=float(receivable),
        independent_completeness_attested=False,
    )


def retired_link(pages, mapping):
    """Require explicit old A-share and new retired-code labels in original text."""
    old_codes, new_codes, evidence = set(), set(), []
    for j, page in enumerate(pages):
        text = compact(page)
        old = re.findall(
            r"(?:上市公司阶段(?:的)?股票代码|原(?:A股)?(?:股票|证券)代码|终止上市(?:的)?股票代码)[:为]?([036]\d{5})",
            text,
        )
        section = re.search(
            r"(?:股票终止上市的情况|终止上市股票种类)(.+?)(?:二、|$)", text
        )
        if section:
            old.extend(re.findall(r"股票代码[:为]?([036]\d{5})", section[1]))
        new = re.findall(
            r"(?:确权(?:证券)?代码[（(][^）)]{0,30}[）)]|确权(?:证券)?代码|挂牌退市板块后的股票代码|挂牌后的股票代码|证券代码)[:为]?(400\d{3})",
            text,
        )
        old_codes.update(old)
        new_codes.update(new)
        if old or new:
            evidence.append((j + 1, text[:1800]))
    if len(old_codes) != 1 or len(new_codes) != 1:
        return []
    old, new = next(iter(old_codes)), next(iter(new_codes))
    if len(mapping.get(old, set())) != 1:
        return []
    return [
        dict(
            security_id=next(iter(mapping[old])),
            old_code=old,
            retired_code=new,
            physical_page=evidence[0][0],
            physical_pages=json.dumps([p for p, _ in evidence]),
            exact_clause="\n".join(f"page {p}: {t}" for p, t in evidence),
            legal_equity_continuity_evidence=True,
            actual_transfer_or_sale_proven=False,
        )
    ]


def build():
    version = code_version(__file__)
    mapping = security_map()
    links, clauses, timelines = [], [], []
    for folder in ["core", "retirement"]:
        for p, r in documents(folder):
            if r["status"] != "ORIGINAL_PDF_RECOVERED":
                continue
            if folder == "core" and r["evidence_kind"] not in [
                "TERMINAL_OR_RELISTING",
                "MERGER_OR_CASH_OPTION",
            ]:
                continue
            source = r["source"]
            pages = original_pages(source["archive_path"], source["sha256"])
            for link in retired_link(pages, mapping):
                links.append(
                    dict(
                        **link,
                        art_code=p.stem,
                        notice_date=r["announcement"]["notice_date"][:10],
                        source_sha256=source["sha256"],
                        source_uri=source["url"],
                        index_sha256=r["announcement"]["index_sha256"],
                    )
                )
            # Archive exact arrangements without pretending a promised transfer occurred.
            for j, page in enumerate(pages):
                t = compact(page)
                for m in re.finditer(
                    r"[^。]{0,120}(?:退市板块|两网公司及退市公司|股份确权|换股登记|换股结果)[^。]{0,180}[。]?",
                    t,
                ):
                    clauses.append(
                        dict(
                            art_code=p.stem,
                            physical_page=j + 1,
                            exact_clause=m[0],
                            source_sha256=source["sha256"],
                            source_uri=source["url"],
                            evidence_status="ORIGINAL_ARRANGEMENT_CLAUSE_REQUIRES_EVENT_REVIEW",
                            actual_receipt_or_account_settlement_confirmed=False,
                        )
                    )
    pixel_reviews = V3 / "reviewed/scanned_equity_links.json"
    if pixel_reviews.exists():
        for reviewed in json.loads(pixel_reviews.read_text()):
            links.append({k: v for k, v in reviewed.items() if k != "images"})
    # These pre-reviewed contract facts retain their original evidence and clocks.
    reviewed = pd.read_parquet(V2_RELEASE / "normalized/reviewed_facts.parquet")
    decoded = reviewed.copy()
    decoded["decoded"] = decoded.value.map(json.loads)
    inv_path = V3 / "normalized/securities.parquet"
    inv = pd.read_parquet(inv_path) if inv_path.exists() else inventory()
    for instrument in ["SZ000748", "SH600005"]:
        sid = inv.loc[inv.instrument.eq(instrument), "security_id"].iloc[0]
        f = decoded[
            decoded.security_id.eq(sid) & decoded.field.str.startswith("merger:")
        ]
        values = dict(zip(f.field, f.decoded))
        if not values:
            continue
        ratio = (
            Fraction("1") / Fraction(str(values["merger:old_shares_per_new_share"]))
            if "merger:old_shares_per_new_share" in values
            else Fraction(str(values["merger:new_shares_per_old_share"]))
        )
        timelines.append(
            dict(
                security_id=sid,
                instrument=instrument,
                successor_instrument=values["merger:successor_instrument"],
                new_shares_per_old_share_rational=str(ratio),
                scheduled_new_listing_date=values["merger:new_shares_listing_date"],
                source_sha256s=json.dumps(sorted(set(f.source_sha256))),
                source_records=json.dumps(f.record_id.tolist()),
                contractual_share_exchange_proven=True,
                actual_account_delivery_confirmed=False,
                fractional_allocation_confirmed=False,
                terminal_wealth=None,
                reason="CONTRACT_RATIO_IS_NOT_AN_ACCOUNT_SETTLEMENT_OR_EXECUTABLE_TERMINAL_VALUE",
            )
        )
    out = V3 / "normalized"
    out.mkdir(parents=True, exist_ok=True)
    for name, data in [
        ("retired_equity_links", links),
        ("terminal_rights_clauses", clauses),
        ("merger_rights_contracts", timelines),
    ]:
        pd.DataFrame(data).to_parquet(out / (name + ".parquet"), index=False)
        # Lengthy original paragraphs stay in the private exchange layer.
        public = pd.DataFrame(data).drop(columns=["exact_clause"], errors="ignore")
        public.to_csv(PUBLIC3 / (name + ".csv"), index=False)
    retired = inv[inv.delist_date.ge("2017-01-03")].copy()
    linked = {r["security_id"] for r in links}
    retired["original_retired_code_link_found"] = retired.security_id.isin(linked)
    retired["terminal_wealth"] = None
    retired["terminal_status"] = "UNKNOWN_NO_ACCOUNT_EQUITY_OR_CASH_SETTLEMENT_PROOF"
    retired[
        [
            "security_id",
            "instrument",
            "board_bucket",
            "delist_date",
            "original_retired_code_link_found",
            "terminal_wealth",
            "terminal_status",
        ]
    ].to_csv(PUBLIC3 / "retired_terminal_coverage.csv", index=False)
    write_json(
        PUBLIC3 / "terminal_rights_summary.json",
        dict(
            retired_since_2017=len(retired),
            original_code_link_assertions=len(links),
            linked_securities=len(linked),
            linked_target_retired_securities=int(
                retired.security_id.isin(linked).sum()
            ),
            original_arrangement_clauses=len(clauses),
            source_reviewed_merger_contracts=len(timelines),
            terminal_wealth_known=0,
            default_zero_values_created=0,
            transform_sha256=version,
        ),
    )


if __name__ == "__main__":
    build()
