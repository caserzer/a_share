"""Descriptive audit of fixed R01 outcomes; no replacement labels or signals."""
import json
import numpy as np
import pandas as pd
from audit_local_inputs import EP, PRIOR, sha


def main():
    out = EP / 'outputs/r01'
    target = out / 'failure_audit.json'
    if target.exists():
        raise FileExistsError(target)
    f = pd.read_parquet(out / 'evaluated_new_observations.parquet')
    p = pd.read_parquet(EP / 'outputs/r00_metric_denominators/full_process_registry.parquet')
    rawfile = PRIOR / 'daily_industries.parquet'
    raw = pd.read_parquet(rawfile)
    groups = {k: g.set_index('day_i').sort_index() for k, g in raw.groupby(['era', 'industry_code'])}
    rows = []
    checked = 0
    for r in f.itertuples():
        g = groups[(r.era, r.industry_code)]
        if r.post_evaluation in ('POST_VALID', 'POST_FAILED'):
            w = g.reindex(range(r.day, r.day + 61))
            v = w.nav.to_numpy(float)
            assert np.isfinite(v).all() and (v > 0).all() and w.block.nunique() == 1
            returns = v[1:] / v[0] - 1
            # Independent arithmetic against frozen numerical contract, no evaluator import.
            checks = [max(returns[:20]) >= .08, returns[-1] >= .05,
                      sum(returns >= .02) >= 40, min(returns) >= -.05,
                      min(v / np.maximum.accumulate(v) - 1) >= -.12]
            assert all(checks) == (r.post_evaluation == 'POST_VALID'), r.alert_id
            checked += 1
        if r.outcome != 'UNMATCHED_FAILURE':
            continue
        candidates = p[(p.era == r.era) & (p.industry_code == r.industry_code)
                       & ~p.left_origin_uncertain
                       & (r.day - p.start_day_i).between(11, 60)]
        chosen = candidates.sort_values(['start_day_i', 'process_id']).iloc[-1] if len(candidates) else None
        rows.append(dict(alert_id=r.alert_id, late_reference_exists=chosen is not None,
                         late_process_id=None if chosen is None else chosen.process_id,
                         delay=None if chosen is None else int(r.day-chosen.start_day_i),
                         post_evaluation=r.post_evaluation,
                         prior_process_gain=None if chosen is None else float(g.loc[r.day, 'nav']/g.loc[chosen.start_day_i, 'nav']-1)))
    d = pd.DataFrame(rows)
    old = pd.read_parquet(out/'unmatched_timing_diagnostic.parquet').set_index('alert_id')
    assert d.set_index('alert_id').late_reference_exists.sort_index().equals(old.late_reference_exists.sort_index())
    d.to_parquet(out/'failure_audit_rows.parquet', index=False)
    result = dict(scope='Descriptive timing attribution only; late references are not matched successes',
                  arithmetic_checked=checked, arithmetic_disagreements=0,
                  unmatched=len(d), cross_counts=d.groupby(['late_reference_exists','post_evaluation']).size().rename('n').reset_index().to_dict('records'),
                  late_delay=d.delay.dropna().describe(percentiles=[.1,.5,.9,.95]).to_dict(),
                  late_prior_gain=d.prior_process_gain.dropna().describe(percentiles=[.1,.5,.9,.95]).to_dict(),
                  inputs={str(x):sha(x) for x in [rawfile,out/'evaluation.json',out/'evaluated_new_observations.parquet',EP/'outputs/r00_metric_denominators/full_process_registry.parquet',EP/'src/r01_failure_audit.py']})
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='inputs'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
