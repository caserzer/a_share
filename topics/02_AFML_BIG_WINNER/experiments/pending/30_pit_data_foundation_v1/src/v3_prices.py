"""Add exchange-hosted observations and fail closed on unreconciled field conflicts."""

import json
import numpy as np
import pandas as pd
from archive import write_json
from v3_core import V3, PUBLIC3, V2_RELEASE, read_verified, code_version

FIELDS = ["open", "high", "low", "close", "volume", "money"]


def build():
    inv = pd.read_parquet(V3 / "normalized/securities.parquet").set_index("instrument")
    conflicts, summaries = [], []
    recovered_fields = {field: 0 for field in FIELDS}
    target = V3 / "normalized/prices"
    target.mkdir(parents=True, exist_ok=True)
    for p in sorted((V3 / "acquired/exchange_quotes").glob("*.parquet")):
        instrument = p.stem
        sid = inv.loc[instrument].security_id
        official, rec = read_verified(p)
        if official.empty:
            continue
        official = official[
            official.date.between("2017-01-03", "2026-10-21")
        ].set_index("date")
        basepath = V2_RELEASE / f"normalized/prices/{sid}.parquet"
        old = (
            pd.read_parquet(basepath)
            if basepath.exists()
            else pd.DataFrame(columns=["date", *FIELDS])
        )
        if any(
            field in old and old[field].notna().any()
            for field in ["can_buy", "can_sell"]
        ):
            raise ValueError(
                "explicit source execution flags need individual reconciliation"
            )
        result = old.set_index("date").copy()
        new_dates = official.index.difference(result.index)
        extra = pd.DataFrame(index=new_dates, columns=result.columns)
        for field in FIELDS:
            extra[field] = official.loc[new_dates, field]
            extra[field + "_conflict"] = False
        extra["security_id"] = sid
        extra["quality_tier"] = "Historical-proxy"
        for col, value in [
            ("source_sha256s", rec["sha256"]),
            ("source_providers", "SSE_HOSTED_CURRENT_HISTORY"),
        ]:
            extra[col] = pd.Series([[value] for _ in new_dates], index=new_dates)
        result = pd.concat([result, extra], axis=0).sort_index()
        overlap = result.index.intersection(official.index)
        recovered = 0
        for field in FIELDS:
            lhs = pd.to_numeric(result.loc[overlap, field], errors="coerce")
            rhs = pd.to_numeric(official.loc[overlap, field], errors="coerce")
            different = (
                lhs.notna()
                & rhs.notna()
                & (lhs - rhs).abs().gt(0.51 if field == "money" else 1e-7)
            )
            for day in overlap[different]:
                conflicts.append(
                    dict(
                        instrument=instrument,
                        security_id=sid,
                        date=day,
                        field=field,
                        v2_value=result.at[day, field],
                        exchange_hosted_value=official.at[day, field],
                        v2_source_sha256s=json.dumps(
                            list(result.at[day, "source_sha256s"])
                        ),
                        exchange_source_sha256=rec["sha256"],
                        resolution="UNKNOWN_PRESERVE_BOTH_OBSERVATIONS",
                    )
                )
            result.loc[overlap[different], field] = np.nan
            result.loc[overlap[different], field + "_conflict"] = True
            # Fill only a previously absent field, never an existing unresolved conflict.
            prior_conflict = (
                result.loc[overlap, field + "_conflict"].fillna(False).astype(bool)
            )
            recover = lhs.isna() & rhs.notna() & ~prior_conflict
            result.loc[overlap[recover], field] = rhs.loc[recover]
            recovered += int(recover.sum())
            recovered_fields[field] += int(recover.sum())
        result["exchange_hosted_source_sha256"] = pd.Series(
            rec["sha256"], index=official.index
        ).reindex(result.index)
        # No execution flag is inferred from an exchange-hosted daily observation.
        result["can_buy"] = None
        result["can_sell"] = None
        result.reset_index(names="date").to_parquet(
            target / f"{sid}.parquet", index=False
        )
        summaries.append(
            dict(
                instrument=instrument,
                security_id=sid,
                baseline_rows=len(old),
                exchange_rows=len(official),
                new_security_dates=len(new_dates),
                previously_missing_fields_recovered=recovered,
                output_rows=len(result),
            )
        )
    pd.DataFrame(conflicts).to_csv(
        PUBLIC3 / "exchange_field_conflicts.csv", index=False
    )
    pd.DataFrame(summaries).to_csv(
        PUBLIC3 / "exchange_price_overlay_coverage.csv", index=False
    )
    write_json(
        PUBLIC3 / "exchange_overlay_summary.json",
        dict(
            overlay_securities=len(summaries),
            new_security_dates=sum(r["new_security_dates"] for r in summaries),
            previously_missing_fields_recovered=sum(
                r["previously_missing_fields_recovered"] for r in summaries
            ),
            recovered_fields=recovered_fields,
            new_unresolved_field_conflicts=len(conflicts),
            conflict_fields=pd.DataFrame(conflicts).field.value_counts().to_dict()
            if conflicts
            else {},
            positive_execution_flags_created=0,
            transform_sha256=code_version(__file__),
        ),
    )


if __name__ == "__main__":
    build()
