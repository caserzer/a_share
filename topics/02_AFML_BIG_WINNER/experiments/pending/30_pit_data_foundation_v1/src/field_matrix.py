"""Per-field x security x year x board proxy observations, without invented denominators."""

import pandas as pd
from archive import EP, CACHE


def main():
    inv = pd.read_parquet(CACHE / "identity/security_inventory.parquet")
    result = []
    for r in inv.itertuples():
        for domain, path, date_col, fields in [
            (
                "raw_prices",
                CACHE / f"prices/{r.security_id}.parquet",
                "date",
                ["open", "high", "low", "close", "volume", "money", "turnover_rate"],
            ),
            (
                "shares",
                CACHE / f"shares/{r.security_id}.parquet",
                "effective_date",
                ["total_shares"],
            ),
            (
                "financials",
                CACHE / f"proxy/financials/{r.instrument[2:]}.{r.exchange}.parquet",
                "REPORT_DATE",
                [
                    "EPSJB",
                    "BPS",
                    "PARENTNETPROFIT",
                    "TOTALOPERATEREVE",
                    "ROEJQ",
                    "ZCFZL",
                    "MGJYXJJE",
                ],
            ),
            (
                "valuation",
                CACHE / f"proxy/valuation/{r.instrument[2:]}.parquet",
                "TRADE_DATE",
                [
                    "PE_TTM",
                    "PB_MRQ",
                    "PS_TTM",
                    "TOTAL_MARKET_CAP",
                    "CLOSE_PRICE",
                    "TOTAL_SHARES",
                ],
            ),
        ]:
            if not path.exists():
                continue
            f = pd.read_parquet(path)
            dates = pd.to_datetime(f[date_col], errors="coerce")
            f = f[dates.ge("2017-01-01")].copy()
            f["_year"] = dates.loc[f.index].dt.year
            for year, g in f.groupby("_year"):
                for field in fields:
                    values = (
                        pd.to_numeric(g[field], errors="coerce")
                        if field in g
                        else pd.Series(dtype=float)
                    )
                    result.append(
                        dict(
                            domain=domain,
                            field=field,
                            instrument=r.instrument,
                            security_id=r.security_id,
                            year=int(year),
                            board=r.board_bucket,
                            source_rows=len(g),
                            non_null=int(values.notna().sum()),
                            null_or_absent=len(g) - int(values.notna().sum()),
                            certified_first_vintage_rows=0,
                            denominator="cached_records_only_population_denominator_UNKNOWN",
                        )
                    )
    out = EP / "outputs/audits"
    full = pd.DataFrame(result)
    full.to_csv(
        out / "field_security_year_coverage.csv.gz",
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )
    grouped = full.groupby(
        ["domain", "field", "year", "board", "denominator"], as_index=False
    ).agg(
        source_rows=("source_rows", "sum"),
        non_null=("non_null", "sum"),
        null_or_absent=("null_or_absent", "sum"),
        securities=("security_id", "nunique"),
        certified_first_vintage_rows=("certified_first_vintage_rows", "sum"),
    )
    grouped["observed_non_null_fraction"] = grouped.non_null / grouped.source_rows
    grouped["strict_gate"] = "BLOCKED"
    grouped.to_csv(out / "field_year_board_matrix.csv", index=False)
    print("field matrix", len(full), "security/year/field cells", flush=True)


if __name__ == "__main__":
    main()
