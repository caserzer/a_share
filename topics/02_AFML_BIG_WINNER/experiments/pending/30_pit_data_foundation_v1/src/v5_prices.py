"""Separate qfq OHLC from frozen unadjusted bars; reconcile code-change scales."""
import json
import os
import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from archive import EP, append_receipt, archive_bytes, sha, write_json
from v5_core import V5, PUBLIC, baseline, pin_sources, price_input
from v5_factors import apply_factors, parse_factors


def compatible_scale(primary, other, start, end):
    """All factor steps in the shared historical interval must have one ratio.

    Current factors can use different scalar anchors after a continuous code change.
    Matching only the last quote or a single factor date does not establish this.
    """
    dates = pd.DatetimeIndex(sorted(set(primary.date) | set(other.date) | {pd.Timestamp(start), pd.Timestamp(end)}))
    dates = dates[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))]
    if not len(dates):
        return None
    samples = pd.DataFrame({"date": dates})
    a = pd.merge_asof(samples, primary, on="date", direction="backward").qfq_divisor
    b = pd.merge_asof(samples, other, on="date", direction="backward").qfq_divisor
    ratio = a / b
    if ratio.isna().any() or not np.isfinite(ratio).all() or not ratio.gt(0).all():
        return None
    scale = float(ratio.iloc[-1])
    return scale if np.allclose(ratio, scale, rtol=1e-8, atol=1e-10) else None


def load_factor(instrument):
    p = V5 / f"acquired/factors/{instrument}.parquet"
    if not p.exists():
        return None, None
    rec = json.loads(Path(str(p) + ".receipt.json").read_text())
    if sha(p) != rec["parquet_sha256"]:
        raise ValueError("changed factor partition")
    body = V5 / "raw/sha256" / rec["sha256"][:2] / rec["sha256"]
    if sha(body) != rec["sha256"]:
        raise ValueError("changed raw factor response")
    factors = parse_factors(body.read_bytes(), instrument)
    pd.testing.assert_frame_equal(factors, pd.read_parquet(p))
    return factors, rec["sha256"]


def build_security(raw, primary_instrument, intervals):
    result = raw.sort_values("date").copy()
    if result.empty:
        for col in ["open", "high", "low", "close"]:
            result["qfq_" + col] = pd.Series(dtype=float)
        for col in ["qfq_divisor", "factor_alias_scale"]:
            result[col] = pd.Series(dtype=float)
        for col in ["factor_source_instrument", "factor_source_sha256", "factor_series_instrument", "factor_chain_id"]:
            result[col] = pd.Series(dtype=object)
        result["factor_effective_date"] = pd.to_datetime([])
        return result, []
    result["factor_source_instrument"] = primary_instrument
    if "code_interval_source_instrument" in result:
        result["factor_source_instrument"] = result.code_interval_source_instrument.fillna(primary_instrument)
    elif len(intervals):
        for r in intervals.to_dict("records"):
            start = r.get("valid_from")
            end = r.get("valid_to", r.get("valid_until_exclusive"))
            keep = pd.Series(True, index=result.index)
            if pd.notna(start):
                keep &= result.date.ge(pd.Timestamp(start))
            if pd.notna(end):
                keep &= result.date.lt(pd.Timestamp(end))
            result.loc[keep, "factor_source_instrument"] = r.get("historical_instrument", r.get("instrument"))
    primary, _ = load_factor(primary_instrument)
    pieces, links = [], []
    for instrument, part in result.groupby("factor_source_instrument", sort=True):
        factors, digest = load_factor(instrument)
        canonical_alias_fallback = factors is None and primary is not None and len(intervals) > 0
        if canonical_alias_fallback:
            # The vendor's full current-code history belongs to the same mapped
            # security. This remains a retrospective alias proxy, not an
            # independently corroborated old-code factor series.
            factors, digest = load_factor(primary_instrument)
        # Use current alias only when its entire step history agrees up to a scalar.
        scale = None
        if factors is not None and primary is not None:
            scale = compatible_scale(primary, factors, part.date.min(), part.date.max())
        if factors is None:
            adjusted = apply_factors(part, pd.DataFrame({"date": pd.to_datetime([]), "qfq_divisor": []}))
        else:
            adjusted = apply_factors(part, factors)
        adjusted["factor_source_sha256"] = digest
        adjusted["factor_series_instrument"] = primary_instrument if canonical_alias_fallback else instrument
        adjusted["factor_alias_scale"] = scale
        adjusted["factor_chain_id"] = instrument if scale is None else primary_instrument
        if scale is not None:
            adjusted["qfq_divisor"] *= scale
            for col in ["open", "high", "low", "close"]:
                adjusted["qfq_" + col] /= scale
        pieces.append(adjusted)
        links.append(dict(instrument=instrument, primary_instrument=primary_instrument, rows=len(part),
                          scalar_to_primary=scale, shared_step_curve_matched=scale is not None and not canonical_alias_fallback,
                          canonical_series_fallback=canonical_alias_fallback,
                          source_sha256=digest))
    return pd.concat(pieces).sort_values("date").reset_index(drop=True), links


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stream", action="store_true", help="wait for the bounded factor collector as it progresses")
    args = parser.parse_args()
    versions = pin_sources()
    inv = pd.read_parquet(baseline("normalized/securities.parquet"))
    continuous = pd.read_parquet(baseline("normalized/code_intervals.parquet"))
    bse = pd.read_parquet(baseline("inputs/baseline/normalized/code_intervals.parquet"))
    audits, links, comparisons = [], [], []
    out = V5 / "normalized/prices_qfq"
    out.mkdir(parents=True, exist_ok=True)
    legacy = EP.parents[2] / "data/raw/akshare/day/qfq"
    legacy_catalog_path = V5 / "legacy_qfq_inputs.json"
    legacy_catalog = json.loads(legacy_catalog_path.read_text()) if legacy_catalog_path.exists() else {}
    for i, r in enumerate(inv.sort_values("instrument").itertuples()):
        source = price_input(r.security_id)
        if source is None:
            audits.append(dict(security_id=r.security_id, instrument=r.instrument, board_bucket=r.board_bucket,
                               raw_rows=0, qfq_rows=0, reason="MISSING_RAW_PRICES"))
            continue
        raw = pd.read_parquet(source)
        raw["date"] = pd.to_datetime(raw.date)
        if raw.date.duplicated().any():
            raise ValueError("duplicate canonical raw dates")
        intervals = continuous[continuous.security_id.eq(r.security_id)]
        if intervals.empty:
            intervals = bse[bse.security_id.eq(r.security_id)]
        if args.stream:
            needed = {r.instrument}
            if "code_interval_source_instrument" in raw:
                needed.update(raw.code_interval_source_instrument.dropna())
            elif len(intervals):
                field = "historical_instrument" if "historical_instrument" in intervals else "instrument"
                needed.update(intervals[field].dropna())
            while not all((V5 / f"acquired/factors/{x}.parquet.receipt.json").exists() or
                          (V5 / f"acquired/factors/{x}.unresolved.json").exists() for x in needed):
                if (V5 / "provider_gates/finance.sina.com.cn.stop").exists():
                    raise PermissionError("factor provider stopped")
                time.sleep(0.5)
        adjusted, chain_links = build_security(raw, r.instrument, intervals)
        links.extend(dict(x, security_id=r.security_id) for x in chain_links)
        adjusted["adjustment_basis"] = "qfq"
        adjusted["adjustment_quality"] = "Historical-proxy"
        adjusted["adjustment_method"] = "raw_OHLC_divided_by_Sina_qfq_divisor_no_rounding"
        temporary = out / f"{r.security_id}.parquet.tmp"
        adjusted.to_parquet(temporary, index=False)
        temporary.replace(out / f"{r.security_id}.parquet")
        valid = adjusted.qfq_open.gt(0) & adjusted.qfq_close.gt(0)
        cached_legacy = r.instrument in legacy_catalog or (not os.environ.get("EP30_V5_OFFLINE") and (legacy / f"{r.instrument}.csv").exists())
        audits.append(dict(security_id=r.security_id, instrument=r.instrument, board_bucket=r.board_bucket,
                           raw_rows=len(raw), qfq_rows=int(valid.sum()), missing_factor_rows=int(adjusted.qfq_divisor.isna().sum()),
                           non_unit_factor_rows=int((adjusted.qfq_divisor.notna() & ~np.isclose(adjusted.qfq_divisor, 1)).sum()),
                           first_raw_date=str(raw.date.min().date()), last_raw_date=str(raw.date.max().date()),
                           independent_qfq_cache_exists=cached_legacy,
                           raw_input_sha256=sha(source), reason="EMPTY_RAW_PRICES" if raw.empty else "QFQ_DIVISOR_APPLIED" if valid.any() else "MISSING_QFQ_FACTORS"))
        # Earlier qfq vintages differ by a global scalar; compare normalized curves,
        # allowing the two-decimal rounding in the old vendor adapter.
        oldpath = legacy / f"{r.instrument}.csv"
        if cached_legacy and valid.any():
            if r.instrument in legacy_catalog:
                oldhash = legacy_catalog[r.instrument]
                bodypath = V5 / "raw/sha256" / oldhash[:2] / oldhash
                assert sha(bodypath) == oldhash
            else:
                bodypath, oldhash = archive_bytes(oldpath.read_bytes(), root=V5)
                legacy_catalog[r.instrument] = oldhash
            old = pd.read_csv(bodypath, usecols=["date", "open", "close"])
            old.date = pd.to_datetime(old.date)
            joined = adjusted[["date", "qfq_open", "qfq_close", "open_conflict", "close_conflict"]].merge(old, on="date", how="inner")
            joined = joined[joined.qfq_close.gt(0) & joined.close.gt(0)]
            if len(joined):
                anchor = joined.iloc[-1]
                scale = anchor.qfq_close / anchor.close
                for col in ["open", "close"]:
                    tolerance = 0.0051 * (abs(scale) + joined["qfq_"+col].abs()/anchor.close) + 1e-8
                    err = (joined["qfq_"+col] - joined[col]*scale).abs()
                    comparisons.append(dict(security_id=r.security_id, instrument=r.instrument, field=col,
                        rows=len(joined), rescale_anchor=str(anchor.date.date()), scalar=float(scale),
                        within_legacy_rounding_tolerance=int(err.le(tolerance).sum()),
                        raw_conflict_rows=int(joined[col+"_conflict"].fillna(False).sum()),
                        max_absolute_difference=float(err.max()), legacy_qfq_sha256=oldhash))
        if i % 250 == 0:
            print("qfq prices", i, "/", len(inv), flush=True)
    pd.DataFrame(audits).to_csv(PUBLIC / "price_adjustment_coverage.csv", index=False)
    write_json(legacy_catalog_path, legacy_catalog)
    pd.DataFrame(links).to_csv(PUBLIC / "code_factor_scale_links.csv", index=False)
    pd.DataFrame(comparisons).to_csv(PUBLIC / "legacy_qfq_comparison.csv", index=False)
    write_json(PUBLIC / "price_audit.json", dict(
        baseline_price_basis="unadjusted", baseline_adjustflag="3", qfq_formula="raw_OHLC / effective_Sina_qfq_divisor",
        factor_join="backward-asof only; missing predecessor remains missing", no_rounding=True,
        qfq_is_retrospective_price_return_proxy=True, feature_pit_certified=False,
        securities=len(inv), raw_rows=sum(x["raw_rows"] for x in audits), qfq_rows=sum(x["qfq_rows"] for x in audits),
        securities_with_qfq=sum(x["qfq_rows"]>0 for x in audits), transform_source_hashes=versions))


if __name__ == "__main__":
    main()
