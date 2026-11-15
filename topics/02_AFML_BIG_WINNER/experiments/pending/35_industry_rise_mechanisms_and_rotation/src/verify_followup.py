"""Cross-artifact checks for stock mapping, missing marks, and financial timing."""
import pandas as pd
from common import *


def run():
    keys=['era','level','method','origin'];r4=pd.read_csv(ROOT/'outputs/r04/intervals.csv',parse_dates=['origin','entry','exit'])
    r6=pd.read_csv(ROOT/'outputs/r06/intervals.csv',parse_dates=['origin','entry','exit'])
    for name in ['r06','r07']:
        receipt=json.loads((ROOT/f'outputs/{name}/receipt.json').read_text());assert sha(ROOT/f'protocols/{name}.json')==receipt['protocol_sha256']
    assert not r6.duplicated(keys).any()
    merged=r4.merge(r6,on=keys,how='outer',suffixes=('_r4','_r6'),indicator=True,validate='one_to_one')
    assert merged._merge.eq('both').all()
    assert merged.entry_r4.eq(merged.entry_r6).all() and merged.exit_r4.eq(merged.exit_r6).all()
    assert merged.status_r4.eq('insufficient_signal_universe').equals(merged.status_r6.eq('insufficient_signal_universe'))
    p=pd.read_parquet(ROOT/'data/r06_stock_positions.parquet');weights=p.groupby(keys).weight.sum();assert np.allclose(weights,1)
    assert not p.duplicated(keys+['security_id']).any()
    assert r6.dropna(subset=['membership_max_date']).membership_max_date.pipe(pd.to_datetime).le(r6.dropna(subset=['membership_max_date']).origin).all()
    q=pd.read_csv(ROOT/'outputs/r06/mark_weight_audit.csv',parse_dates=['origin'])
    assert q.unknown_endpoint_weight.between(-1e-12,1+1e-12).all()
    assert np.allclose(q.conditional_loss_floor,q.known_weighted_return_contribution-q.unknown_endpoint_weight)
    assert q.loc[~q.endpoint_complete,'conditional_endpoint_return'].isna().all()
    j=r6.merge(q,on=keys,validate='one_to_one')
    full=j.status.eq('valuation_complete_execution_unproven')
    assert np.allclose(j.loc[full,'unproven_path_weight'],0)
    assert np.allclose(j.loc[full,'gross_return'],j.loc[full,'conditional_endpoint_return'],atol=1e-12)
    assert (j.loc[~full,'unproven_path_weight']>0).all()
    summary=pd.read_csv(ROOT/'outputs/r06/summary.csv');assert not summary.whole_path_valid.any()
    # All methods/eras must remain missing for full performance; conditional intervals aren't stitched.
    for col in ['cagr','drawdown','beta']:
        if col in summary:assert summary[col].isna().all()
    dates=pd.read_csv(ROOT/'outputs/r07/date_metrics.csv')
    common=dates[(dates.cohort=='matched_all_delays')&(dates.method=='F')]
    assert common.groupby(['level','date','horizon']).ic.nunique(dropna=True).le(1).all()
    cov=pd.read_csv(ROOT/'outputs/r07/coverage.csv')
    assert (cov.common_all_delays<=cov.available).all() and (cov.available<=cov.price_ready).all()
    assert cov.groupby(['level','date']).common_all_delays.nunique().eq(1).all()
    archives=pd.read_csv(ROOT/'outputs/r07/archive_clock_coverage.csv');assert archives.archived_records.eq(0).all()
    # Recheck the no-new-PIT decision against its actual availability/market-membership records.
    c=pd.read_csv(ROOT/'outputs/r08/candidate_relevance.csv')
    assert not ((~c.already_reviewed_issuer)&c.active_at_or_after_available).any()
    js(ROOT/'outputs/followup_verification.json',dict(status='PASS',same_r04_r06_scheduled_intervals=len(merged),
        fixed_stock_position_groups=len(weights),complete_interval_values_matched=int(full.sum()),
        unknown_weights_not_renormalized=True,full_performance_not_invented=True,paired_financial_F_invariant=True,
        strict_archive_clock_not_backdated=True,unreviewed_active_pit_candidates=0,
        limitations=['not proof of real tradability','not sufficient inference months','PDF originals for operating observations still pending authorization/access']))
    print('FOLLOWUP VERIFIED',len(merged),'intervals;',int(full.sum()),'complete valuations;',len(weights),'fixed-stock selections')

if __name__=='__main__':run()
