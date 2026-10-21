"""Append quote-availability evidence to the old bridge; keep its returns unchanged."""

import pandas as pd
from archive import CACHE, archive_bytes, write_json, sha
from backfill_rpc import V2, PUBLIC


def main():
    src = CACHE / "bridge/security_month_labels_expanded.parquet"
    _, source_hash = archive_bytes(src.read_bytes())
    f = pd.read_parquet(src)
    old_columns = list(f)
    f["D2v2_start_raw_close_known"] = False
    f["D2v2_end_raw_close_known"] = False
    f["D2v2_start_vendor_suspended"] = False
    for security, g in f.groupby("security_id"):
        path = V2 / f"normalized/prices/{security}.parquet"
        if not path.exists():
            continue
        bars = pd.read_parquet(path)
        known = bars.loc[bars.close.notna(), "date"]
        f.loc[g.index, "D2v2_start_raw_close_known"] = g.date.isin(known)
        f.loc[g.index, "D2v2_end_raw_close_known"] = g.label_end.isin(known)
        if "vendor_trade_status" in bars:
            stopped = bars.loc[bars.vendor_trade_status.eq("0"), "date"]
            f.loc[g.index, "D2v2_start_vendor_suspended"] = g.date.isin(stopped)
    f["D2v2_label_reason"] = (
        "RAW_QUOTE_RECOVERY_DOES_NOT_CLOSE_EXECUTION_RIGHTS_OR_TERMINAL_SETTLEMENT"
    )
    pd.testing.assert_frame_equal(f[old_columns], pd.read_parquet(src))
    f.to_parquet(
        V2 / "normalized/legacy_bridge_with_v2_quote_availability.parquet", index=False
    )
    f.groupby("date").agg(
        rows=("security_id", "size"),
        legacy_start_quote=("start_quote", "sum"),
        v2_raw_close_known=("D2v2_start_raw_close_known", "sum"),
        v2_end_raw_close_known=("D2v2_end_raw_close_known", "sum"),
    ).reset_index().to_csv(
        PUBLIC / "bridge_quote_availability_by_month.csv", index=False
    )
    f.groupby("instrument").agg(
        months=("security_id", "size"),
        legacy_start_quote=("start_quote", "sum"),
        v2_raw_close_known=("D2v2_start_raw_close_known", "sum"),
    ).reset_index().to_csv(
        PUBLIC / "bridge_quote_availability_by_security.csv", index=False
    )
    write_json(
        PUBLIC / "bridge_quote_availability_summary.json",
        dict(
            common_v1_bridge_rows=len(f),
            first_origin=str(f.date.min().date()),
            last_origin=str(f.date.max().date()),
            legacy_columns_unchanged=True,
            legacy_bridge_source_sha256=source_hash,
            legacy_start_quote_rows=int(f.start_quote.sum()),
            v2_start_raw_close_known_rows=int(f.D2v2_start_raw_close_known.sum()),
            newly_observed_raw_close_on_legacy_missing_origin=int(
                (~f.start_quote.eq(True) & f.D2v2_start_raw_close_known).sum()
            ),
            raw_close_became_unknown_on_legacy_origin=int(
                (f.start_quote.eq(True) & ~f.D2v2_start_raw_close_known).sum()
            ),
            strict_labels_recomputed_or_zero_filled=False,
            compatibility_only_not_new_month_population=True,
            transform_sha256=sha(__file__),
        ),
    )


if __name__ == "__main__":
    main()
