"""P1: full-population causal feature and event-label assembly, private payloads."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import OUT, cache, sha, source_manifest, utc_now, write_json
from ep30_adapter import EP30Adapter, h09_gate
from episode_builder import observation_masks
from labels_and_maturity import future_variance, infer_labels
from volume_price_features import build_features

HORIZONS = [5, 10, 20, 60, 120, "6_calendar_months"]


def compare_monthly(new, old):
    joined = old.merge(new, on="date", suffixes=("_old", "_new"), validate="one_to_one")
    counts = dict(rows=len(old), compared=len(joined), mismatches=0)
    for field in ["status", "reason", "entry_date", "exit_date", "mature_at", "value", "raw_price_return", "mfe", "mae"]:
        a, b = joined[field + "_old"], joined[field + "_new"]
        if field in {"value", "raw_price_return", "mfe", "mae"}:
            same = np.isclose(a.to_numpy(float), b.to_numpy(float), atol=1e-10, rtol=1e-8, equal_nan=True)
        else:
            same = (a.eq(b) | (a.isna() & b.isna())).to_numpy()
        counts[field + "_mismatches"] = int((~same).sum())
        counts["mismatches"] += int((~same).sum())
    return counts


def main():
    adapter = EP30Adapter()
    root = cache() / "data"
    if (root / "COMPLETE.json").exists():
        raise RuntimeError("completed data must not be overwritten; use audit/replay")
    root.mkdir(parents=True, exist_ok=True)
    monthly = {h: adapter.read(f"normalized/labels/{h}_price.parquet").groupby("security_id", sort=False)
               for h in ["20_sessions", "60_sessions", "120_sessions", "6_calendar_months"]}
    provider = adapter.read("normalized/labels/20_sessions_price.parquet")
    disagreement = set(provider.loc[provider.qfq_vendor_curve_disagreement, "security_id"])
    del provider
    audit, reconcile, features, labels, coverage = [], [], [], {str(h): [] for h in HORIZONS}, []
    daily_sums = pd.DataFrame(index=adapter.days, data={"mom_sum": 0.0, "rv_sum": 0.0, "count": 0.0})
    market = pd.DataFrame(index=adapter.days, data={"ret_sum": 0.0, "ret_count": 0.0})

    def flush(batch):
        if features:
            p = root / f"features_{batch:03d}.parquet"
            pd.concat(features, ignore_index=True).to_parquet(p, index=False)
            features.clear()
        for h, pieces in labels.items():
            if pieces:
                pd.concat(pieces, ignore_index=True).to_parquet(root / f"labels_{h}_{batch:03d}.parquet", index=False)
                pieces.clear()

    for i, sec in enumerate(adapter.inventory.sort_values("security_id").itertuples()):
        b = adapter.bars(sec.security_id)
        listing = sec.listing_date if pd.notna(sec.listing_date) else sec.bse_listing_proxy
        eligible = (adapter.days >= listing) & (pd.isna(sec.delist_date) | (adapter.days < sec.delist_date)) if pd.notna(listing) else np.zeros(len(adapter.days), bool)
        if b is None or b.empty:
            audit.append(dict(security_id=sec.security_id, board=sec.board_bucket, rows=0, reason="NO_SEALED_PRICES", eligible_weekdays=int(eligible.sum())))
            # Still preserve the eligible denominator for identities with no bars.
            empty = pd.DataFrame(index=range(len(adapter.days)), data=dict(date=adapter.days, observed=False, warmup=False,
                                      relative_turnover=np.nan, breakout=False))
            masks = observation_masks(empty, eligible)
            f = empty.loc[masks["weekly"]].copy()
            for k in masks:
                f[k] = masks[k][masks["weekly"]]
            f["security_id"], f["board"] = sec.security_id, sec.board_bucket
            f["instrument"], f["is_delisted"] = sec.instrument, sec.is_delisted
            f["provider_disagreement"] = sec.security_id in disagreement
            features.append(f)
            continue
        f = build_features(b, adapter.days)
        masks = observation_masks(f, eligible)
        selected = masks["weekly"] | masks["h10_episode"] | masks["h11_episode"]
        frame = f.loc[selected].copy()
        for k, v in masks.items():
            frame[k] = v[selected]
        frame["security_id"], frame["board"] = sec.security_id, sec.board_bucket
        frame["instrument"], frame["is_delisted"] = sec.instrument, sec.is_delisted
        frame["provider_disagreement"] = sec.security_id in disagreement
        features.append(frame)
        active = eligible & f.observed.to_numpy()
        daily_sums["mom_sum"] += f.mom20.where(active).fillna(0).to_numpy()
        daily_sums["rv_sum"] += f.rv20.where(active).fillna(0).to_numpy()
        daily_sums["count"] += (active & f.mom20.notna() & f.rv20.notna()).to_numpy()
        market["ret_sum"] += f.daily_log_return.where(active).fillna(0).to_numpy()
        market["ret_count"] += (active & f.daily_log_return.notna()).to_numpy()
        audit.append(dict(security_id=sec.security_id, board=sec.board_bucket, rows=len(b), reason="HISTORICAL_PROXY",
                          observed=int(f.observed.sum()), warmup=int(f.warmup.sum()), weekly=int(masks["weekly"].sum()),
                          h10_event=int(masks["h10_event"].sum()), h10_episode=int(masks["h10_episode"].sum()),
                          h11_event=int(masks["h11_event"].sum()), h11_episode=int(masks["h11_episode"].sum()),
                          factor_step_200=int(f.factor_step_200.sum()), share_proxy_step_20=int(f.share_proxy_step_20.sum()),
                          turnover_nonnull=int(b.turnover_rate.notna().sum()), st_flag_observations=int(f.vendor_st.notna().sum()),
                          listing_unknown=pd.isna(listing), is_delisted=sec.is_delisted))
        origin_dates = pd.DatetimeIndex(frame.date)
        for h in HORIZONS:
            lab = infer_labels(b, adapter.days, origin_dates, h, sec.delist_date)
            lab["security_id"] = sec.security_id
            lab["trade_time"] = lab.entry_date + pd.Timedelta(hours=9, minutes=30)
            lab["t1"] = lab.exit_date + pd.Timedelta(hours=9, minutes=30)
            lab["quality"] = "Historical-proxy"
            if h == 20:
                lab["future_variance"], lab["rv_mature_at"] = future_variance(f, adapter.days, origin_dates)
            labels[str(h)].append(lab)
            for (year, status), g in lab.groupby([lab.date.dt.year, "status"]):
                coverage.append(dict(horizon=str(h), year=int(year), board=sec.board_bucket, status=status,
                                     rows=len(g), complete_path=int(g.mfe.notna().sum()), delisted=int(sec.is_delisted)*len(g),
                                     delayed_entry=int(g.entry_delay_sessions.gt(0).sum()), delayed_exit=int(g.exit_delay_sessions.gt(0).sum())))
        for h, grouped in monthly.items():
            if sec.security_id in grouped.groups:
                old = grouped.get_group(sec.security_id)
                new = infer_labels(b, adapter.days, old.date, h if h == "6_calendar_months" else int(h.split('_')[0]), sec.delist_date)
                result = compare_monthly(new, old)
                reconcile.append(dict(security_id=sec.security_id, horizon=h, **result))
                if result["mismatches"] or result["compared"] != result["rows"]:
                    write_json(OUT / "audits/monthly_reconciliation_FAILURE.json", dict(security_id=sec.security_id, horizon=h, result=result))
                    raise ValueError("monthly label reconciliation failed")
        if i % 100 == 99:
            flush(i // 100)
            print("P1 securities", i+1, "/", len(adapter.inventory), flush=True)
    flush(len(adapter.inventory)//100)
    # Causal market-state controls; no later stock membership or outcomes.
    m = pd.DataFrame(dict(date=adapter.days, market_mom20=daily_sums.mom_sum / daily_sums['count'].replace(0, np.nan),
                         market_rv20=daily_sums.rv_sum / daily_sums['count'].replace(0, np.nan),
                         market_return=market.ret_sum/market.ret_count.replace(0, np.nan)))
    m.to_parquet(root / "market.parquet", index=False)
    pd.DataFrame(audit).to_csv(OUT / "audits/security_coverage.csv", index=False)
    rec = pd.DataFrame(reconcile)
    rec.groupby("horizon").sum(numeric_only=True).reset_index().to_csv(OUT / "audits/monthly_reconciliation.csv", index=False)
    cov = pd.DataFrame(coverage).groupby(["horizon", "year", "board", "status"]).sum(numeric_only=True).reset_index()
    cov.to_csv(OUT / "audits/label_coverage.csv", index=False)
    # Full per-security reconciliation and raw event denominators remain private.
    rec.to_parquet(root / "monthly_reconciliation.parquet", index=False)
    fields = [
        ("OHLCV_money_turnover", "Historical-proxy", "sealed vendor rows; conflict flags masked"),
        ("qfq_ratio_features", "Historical-proxy", "scalar-reanchor invariant; actual company-action ledger unverified"),
        ("security_identity", "Historical-proxy", "includes delisted; continuous aliases preserved by EP30"),
        ("ST_suspension", "Historical-proxy", "vendor row flags; no daily qualification certification"),
        ("float_cap", "Historical-proxy", "raw close * volume / contemporaneous turnover; no independent shares"),
        ("industry", "UNKNOWN", "no sealed industry version table"),
        ("true_total_return_and_execution", "UNKNOWN", "price aliases used once; cash/terminal/fills unverified"),
        ("trade_size_trade_count", "UNKNOWN", "no timestamp-attested microstructure; H09 BLOCKED_DATA")]
    pd.DataFrame(fields, columns=["field", "quality", "reason"]).to_csv(OUT / "audits/field_quality.csv", index=False)
    manifest = {p.name: sha(p) for p in sorted(root.glob("*.parquet"))}
    write_json(root / "COMPLETE.json", dict(completed_at=utc_now(), files=manifest, sources=source_manifest()))
    write_json(OUT / "manifests/data.json", dict(private_root=str(root), manifest_sha256=sha(root / "COMPLETE.json"),
               partitions=len(manifest), securities=len(adapter.inventory), reconciliation_rows=int(rec.rows.sum()),
               reconciliation_mismatches=int(rec.mismatches.sum()), h09=h09_gate([]), quality="Historical-proxy",
               observation_end=str(adapter.days[-1].date()), raw_labels_are_never_features=True))


if __name__ == "__main__":
    (OUT / "audits").mkdir(parents=True, exist_ok=True)
    main()
