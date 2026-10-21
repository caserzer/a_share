"""Join original contract fields without inventing unspecified ratios or payments."""

import json
import pandas as pd
from archive import write_json
from v3_core import V3, PUBLIC3, V2_RELEASE, code_version
from v3_evidence import calendar


def build():
    dates = pd.read_parquet(V3 / "normalized/distribution_contract_dates.parquet")
    amounts = pd.read_parquet(V3 / "normalized/distribution_contract_amounts.parquet")
    rows, comparisons = [], []
    proxy = pd.read_parquet(V2_RELEASE / "normalized/corporate_actions.parquet")
    cal = calendar()
    for art, f in dates.groupby("art_code"):
        row = dict(
            art_code=art,
            security_id=f.iloc[0].security_id,
            notice_date=f.iloc[0].notice_date,
            known_at=cal.publication_time(f.iloc[0].notice_date),
            source_sha256=f.iloc[0].source_sha256,
            source_uri=f.iloc[0].source_uri,
            actual_payment_date=None,
            actual_payment_confirmed=False,
            full_holding_interval_action_coverage_attested=False,
            quality_tier="PIT-reconstructed",
            coverage_scope="INDIVIDUAL_CONTRACT_FIELDS_ONLY",
        )
        for field in [
            "record_date",
            "ex_date",
            "scheduled_cash_payment_date",
            "scheduled_share_delivery_date",
        ]:
            g = f[f.field.eq(field)]
            row[field] = g.iloc[0].value if len(g) == 1 else None
        a = amounts[amounts.art_code.eq(art)] if len(amounts) else amounts
        for field in [
            "cash_gross_CNY_per_share",
            "bonus_shares_per_share",
            "capitalization_shares_per_share",
        ]:
            g = a[a.field.eq(field)] if len(a) else a
            row[field] = g.iloc[0].value if len(g) == 1 else None
        row["physical_pages"] = json.dumps(
            sorted(set(f.physical_page) | (set(a.physical_page) if len(a) else set()))
        )
        rows.append(row)
        if row["record_date"] and row["ex_date"]:
            match = proxy[
                proxy.security_id.eq(row["security_id"])
                & proxy.record_date.eq(row["record_date"])
                & proxy.ex_date.eq(row["ex_date"])
            ]
            for candidate in match.to_dict("records"):
                for field in [
                    "cash_gross_CNY_per_share",
                    "bonus_shares_per_share",
                    "capitalization_shares_per_share",
                ]:
                    original, vendor = row[field], candidate[field]
                    if original is None or pd.isna(vendor):
                        continue
                    comparisons.append(
                        dict(
                            art_code=art,
                            security_id=row["security_id"],
                            field=field,
                            original_value=original,
                            retrospective_vendor_value=vendor,
                            agrees=abs(float(original) - float(vendor)) < 1e-8,
                            original_source_sha256=row["source_sha256"],
                            vendor_source_sha256=candidate["source_sha256"],
                        )
                    )
    frame = pd.DataFrame(rows)
    frame.to_parquet(
        V3 / "normalized/original_distribution_contracts.parquet", index=False
    )
    frame.to_csv(PUBLIC3 / "original_distribution_contracts.csv", index=False)
    check = pd.DataFrame(comparisons)
    check.to_csv(PUBLIC3 / "distribution_original_vendor_comparison.csv", index=False)
    write_json(
        PUBLIC3 / "original_action_summary.json",
        dict(
            original_contracts=len(frame),
            original_contracts_since_2017=int(
                pd.to_datetime(frame.ex_date).ge("2017-01-03").sum()
            )
            if len(frame)
            else 0,
            explicitly_recovered_cash_payment_schedules=int(
                frame.scheduled_cash_payment_date.notna().sum()
            )
            if len(frame)
            else 0,
            explicitly_recovered_gross_cash_values=int(
                frame.cash_gross_CNY_per_share.notna().sum()
            )
            if len(frame)
            else 0,
            cross_source_field_comparisons=len(check),
            disagreements=int((~check.agrees).sum()) if len(check) else 0,
            actual_cash_receipts_proven=0,
            holding_interval_completeness_attestations=0,
            transform_sha256=code_version(__file__),
        ),
    )


if __name__ == "__main__":
    build()
