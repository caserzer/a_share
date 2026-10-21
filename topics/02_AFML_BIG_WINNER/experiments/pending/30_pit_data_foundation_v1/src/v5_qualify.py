"""Expose cross-provider qfq disagreement without choosing labels by performance."""
import json

import numpy as np
import pandas as pd

from archive import sha, write_json
from v5_core import V5, PUBLIC, pin_sources
from v5_labels import HORIZONS, POLICIES


def main():
    versions = pin_sources()
    curves = pd.read_csv(PUBLIC / "legacy_qfq_comparison.csv")
    catalog = json.loads((V5 / "legacy_qfq_inputs.json").read_text())
    sources, legacy = {}, {}
    for instrument, digest in catalog.items():
        p = V5 / "raw/sha256" / digest[:2] / digest
        assert sha(p) == digest
        source = pd.read_csv(p, usecols=["source_function"], nrows=1).iloc[0,0]
        sources[instrument] = source
    curves["legacy_source_function"] = curves.instrument.map(sources)
    curves["residual_outside_rounding"] = curves.within_legacy_rounding_tolerance.lt(curves.rows)
    curves.to_csv(PUBLIC / "legacy_qfq_method_audit.csv", index=False)
    bad = curves[curves.residual_outside_rounding].drop_duplicates("security_id")
    for r in bad.itertuples():
        digest = catalog[r.instrument]
        p = V5 / "raw/sha256" / digest[:2] / digest
        f = pd.read_csv(p, usecols=["date", "open"])
        f.date = pd.to_datetime(f.date)
        if f.date.duplicated().any():
            raise ValueError("duplicate legacy qfq dates")
        legacy[r.security_id] = pd.Series(pd.to_numeric(f.open, errors="coerce").to_numpy(), index=pd.DatetimeIndex(f.date))
    stats = []
    six_alt = None
    for h in HORIZONS:
        base = pd.read_parquet(V5 / f"normalized/labels/{h}_price.parquet")
        base["qfq_vendor_curve_disagreement"] = base.security_id.isin(legacy)
        base["legacy_qfq_same_dates_return"] = np.nan
        base["legacy_qfq_source_function"] = None
        base["legacy_qfq_minus_primary_return"] = np.nan
        base["loss_threshold_agrees_across_qfq_sources"] = pd.Series(pd.NA, index=base.index, dtype="boolean")
        for sid, old_opens in legacy.items():
            selected = base.security_id.eq(sid) & base.status.eq("KNOWN_INFERRED")
            idx = base.index[selected]
            a = old_opens.reindex(pd.DatetimeIndex(base.loc[idx,"entry_date"])).to_numpy(dtype=float)
            b = old_opens.reindex(pd.DatetimeIndex(base.loc[idx,"exit_date"])).to_numpy(dtype=float)
            alt = np.where((a>0)&(b>0),b/a-1,np.nan)
            base.loc[idx,"legacy_qfq_same_dates_return"] = alt
            instrument = bad.loc[bad.security_id.eq(sid),"instrument"].iloc[0]
            base.loc[idx,"legacy_qfq_source_function"] = sources[instrument]
            valid = np.isfinite(alt)
            comparable = idx[valid]
            base.loc[comparable,"legacy_qfq_minus_primary_return"] = alt[valid] - base.loc[comparable,"value"]
            base.loc[comparable,"loss_threshold_agrees_across_qfq_sources"] = (alt[valid]<-0.2) == base.loc[comparable,"value"].lt(-0.2)
        for policy in POLICIES:
            base["return_policy"] = policy
            base.to_parquet(V5 / f"normalized/labels/{h}_{policy}.parquet", index=False)
        known = base.status.eq("KNOWN_INFERRED")
        comparable = base.legacy_qfq_same_dates_return.notna()
        stats.append(dict(horizon=h, disagreement_security_months=int(base.qfq_vendor_curve_disagreement.sum()),
            known_primary_inferred_with_disagreement=int((known&base.qfq_vendor_curve_disagreement).sum()),
            same_dates_comparable=int(comparable.sum()),
            loss_classification_disagrees=int(base.loss_threshold_agrees_across_qfq_sources.eq(False).sum())))
        if h == "6_calendar_months":
            six_alt = base[["date","security_id","legacy_qfq_same_dates_return","loss_threshold_agrees_across_qfq_sources"]].copy()
    bridge_path = V5 / "normalized/full_monthly_bridge.parquet"
    bridge = pd.read_parquet(bridge_path)
    bridge["v5_qfq_vendor_curve_disagreement"] = bridge.v4_canonical_security_id.isin(legacy)
    add = six_alt.rename(columns={"security_id":"v4_canonical_security_id", "legacy_qfq_same_dates_return":"v5_legacy_qfq_6m_same_dates_return",
        "loss_threshold_agrees_across_qfq_sources":"v5_qfq_6m_loss_threshold_agrees_across_qfq_sources"})
    for col in add.columns.difference(["date","v4_canonical_security_id"]):
        if col in bridge:
            bridge = bridge.drop(columns=col)
    bridge = bridge.merge(add,on=["date","v4_canonical_security_id"],how="left",validate="many_to_one",sort=False)
    bridge.to_parquet(bridge_path,index=False)
    pd.DataFrame(stats).to_csv(PUBLIC / "qfq_provider_sensitivity.csv",index=False)
    write_json(PUBLIC / "qfq_provider_sensitivity.json",dict(
        disagreement_securities=len(legacy), legacy_source_functions=pd.Series(sources).value_counts().to_dict(),
        residual_field_curves_by_source=curves[curves.residual_outside_rounding].legacy_source_function.value_counts().to_dict(),
        main_provider_fixed_before_labels=True, no_adaptive_provider_selection=True,
        numerical_cause_not_independently_resolved=True, primary_values_remain_vendor_price_proxies=True,
        horizons=stats, transform_source_hashes=versions))
    print("provider qualification",len(legacy),stats,flush=True)


if __name__ == "__main__":
    main()
