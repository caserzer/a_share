"""Validate inference invariants, full bridge preservation and frozen v4 hashes."""
import json

import numpy as np
import pandas as pd

from archive import EP, sha, write_json
from v5_core import BASE, V5, PUBLIC, baseline, catalog
from v5_labels import HORIZONS, POLICIES


def main():
    old = pd.read_parquet(baseline("normalized/full_monthly_bridge.parquet"))
    bridge = pd.read_parquet(V5 / "normalized/full_monthly_bridge.parquet")
    pd.testing.assert_frame_equal(old, bridge[old.columns])
    candidate = old[old.v4_provisional_member][["date", "security_id"]].sort_values(["security_id", "date"]).reset_index(drop=True)
    count = known_count = 0
    curves = pd.read_csv(PUBLIC / "legacy_qfq_comparison.csv")
    disagreement_sids = set(curves.loc[curves.within_legacy_rounding_tolerance.lt(curves.rows),"security_id"])
    for h in HORIZONS:
        reference = None
        for policy in POLICIES:
            f = pd.read_parquet(V5 / f"normalized/labels/{h}_{policy}.parquet")
            keys = f[["date", "security_id"]].sort_values(["security_id", "date"]).reset_index(drop=True)
            pd.testing.assert_frame_equal(candidate, keys)
            assert not f.duplicated(["date", "security_id"]).any()
            assert f.quality_tier.eq("Historical-proxy").all()
            assert f.adjustment_basis.eq("qfq").all() and f.execution_assumed.all()
            assert not f.strict_entry_execution_known.any() and not f.strict_exit_execution_known.any()
            assert not f.actual_cash_and_terminal_wealth_verified.any()
            assert f.qfq_vendor_curve_disagreement.eq(f.security_id.isin(disagreement_sids)).all()
            known = f.status.eq("KNOWN_INFERRED")
            assert f.loc[known, "value"].notna().all() and np.isfinite(f.loc[known,"value"]).all()
            assert f.loc[~known,"value"].isna().all()
            assert (f.loc[known,"entry_date"] > f.loc[known,"date"]).all()
            assert (f.loc[known,"entry_date"] < f.loc[known,"target_session"]).all()
            assert (f.loc[known,"exit_date"] > f.loc[known,"entry_date"]).all()
            assert (f.loc[known,"exit_date"] >= f.loc[known,"target_session"]).all()
            assert not f.loc[known,"terminal_rights_required"].any()
            np.testing.assert_allclose(f.loc[known,"value"], f.loc[known,"exit_qfq_open"]/f.loc[known,"entry_qfq_open"]-1)
            assert (f.loc[known,"loss_below_minus20"].astype(bool) == f.loc[known,"value"].lt(-0.2)).all()
            comparable = f.legacy_qfq_same_dates_return.notna()
            assert (known & f.qfq_vendor_curve_disagreement)[comparable].all()
            np.testing.assert_allclose(f.loc[comparable,"legacy_qfq_minus_primary_return"],
                                       f.loc[comparable,"legacy_qfq_same_dates_return"] - f.loc[comparable,"value"])
            assert f.loc[comparable,"loss_threshold_agrees_across_qfq_sources"].eq(
                f.loc[comparable,"legacy_qfq_same_dates_return"].lt(-0.2).eq(f.loc[comparable,"value"].lt(-0.2))).all()
            complete = f.mfe.notna()
            assert f.loc[complete,"path_missing_sessions"].eq(0).all()
            assert (f.loc[complete,"mfe"] >= f.loc[complete,"value"] - 1e-12).all()
            assert (f.loc[complete,"mae"] <= f.loc[complete,"value"] + 1e-12).all()
            actual = f.drop(columns="return_policy")
            if reference is not None:
                pd.testing.assert_frame_equal(reference, actual)
            reference = actual
            count += len(f)
            known_count += int(known.sum())
    # Recheck every byte of the existing immutable v4 release after v5 derivation.
    for name, expected in catalog().items():
        if sha(BASE / name) != expected:
            raise ValueError("changed frozen v4 file: " + name)
    protected = json.loads((EP / "outputs/manifests/prior_preservation.json").read_text())
    for name, expected in protected.items():
        if sha(EP.parents[4] / name) != expected:
            raise ValueError("changed protected prior research: " + name)
    write_json(PUBLIC / "validation.json", dict(status="PASS", label_rows=count, known_inferred_rows=known_count,
        labels_are_not_actual_total_return_or_execution=True, policy_alias_values_equal=True,
        qfq_provider_disagreement_and_comparators_checked=True,
        original_bridge_rows_columns_unchanged=True, no_unknown_zero_fill=True,
        entry_exit_timing_and_path_contract_checked=True, frozen_v4_files_verified=len(catalog()),
        protected_prior_files_verified=len(protected)))
    print("validation PASS", count, known_count, flush=True)


if __name__ == "__main__":
    main()
