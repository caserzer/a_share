"""Quantify mark uncertainty by original weights, without imputing price paths."""
import pandas as pd
from common import *


def summarize_marks(g):
    w=g.weight.to_numpy();known=g.endpoint_usable.to_numpy(bool)
    assert np.isclose(w.sum(),1)
    contribution=float(np.sum(w[known]*g.endpoint_return.to_numpy()[known]))
    missing=float(w[~known].sum())
    return dict(n_stocks=len(g),unknown_endpoint_weight=missing,unproven_path_weight=float(g.loc[~g.full_path_usable,'weight'].sum()),
        known_weighted_return_contribution=contribution,conditional_loss_floor=contribution-missing,
        endpoint_complete=bool(known.all()),conditional_endpoint_return=contribution if known.all() else np.nan,
        finite_upper_bound=bool(known.all()))


def run():
    out=ROOT/'outputs/r06';positions=pd.read_parquet(ROOT/'data/r06_stock_positions.parquet')
    schedule=pd.read_csv(out/'intervals.csv',parse_dates=['origin','entry','exit'])
    mapping=schedule[['era','level','method','origin','entry','exit']].drop_duplicates()
    positions=positions.merge(mapping,on=['era','level','method','origin'],how='left',validate='many_to_one')
    ev=json.loads((out/'receipt.json').read_text());paths={Path(k).stem:Path(k) for k in ev['source_hashes'] if '/normalized/prices_qfq/' in k}
    days=pd.DatetimeIndex(pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').index)
    records=[]
    # One read per stock; date probes are shared across methods/levels before aggregation.
    for i,(sid,g) in enumerate(positions.groupby('security_id',sort=True)):
        p=paths[sid];assert sha(p)==ev['source_hashes'][str(p)]
        f=pd.read_parquet(p,columns=['date','qfq_close','close_conflict','factor_chain_id']).set_index('date').reindex(days)
        v=pd.to_numeric(f.qfq_close).where(f.close_conflict.eq(False)&pd.to_numeric(f.qfq_close).gt(0)).to_numpy()
        chain=pd.factorize(f.factor_chain_id)[0]
        for r in g[['entry','exit']].drop_duplicates().itertuples(index=False):
            lo=days.get_loc(r.entry);hi=days.get_loc(r.exit);c=chain[lo:hi+1];observed=c[c>=0]
            consistent=bool(len(observed) and observed.min()==observed.max())
            endpoint=bool(np.isfinite(v[[lo,hi]]).all() and chain[lo]>=0 and chain[hi]==chain[lo] and consistent)
            full=bool(endpoint and np.isfinite(v[lo:hi+1]).all() and (c>=0).all())
            records.append(dict(security_id=sid,entry=r.entry,exit=r.exit,endpoint_usable=endpoint,full_path_usable=full,
                confirmed_observed_chain_change=bool(len(observed) and observed.min()!=observed.max()),
                unknown_chain_days=int((c<0).sum()),missing_price_days=int((~np.isfinite(v[lo:hi+1])).sum()),
                endpoint_return=v[hi]/v[lo]-1 if endpoint else np.nan))
        if (i+1)%1500==0:print('MARK AUDIT STOCKS',i+1,flush=True)
    marks=pd.DataFrame(records);marks.to_parquet(ROOT/'data/r06_stock_mark_quality.parquet',index=False)
    j=positions.merge(marks,on=['security_id','entry','exit'],validate='many_to_one');results=[]
    keys=['era','level','method','origin','entry','exit']
    for key,g in j.groupby(keys):results.append(dict(zip(keys,key),**summarize_marks(g)))
    results=pd.DataFrame(results);results.to_csv(out/'mark_weight_audit.csv',index=False)
    js(out/'mark_quality_receipt.json',dict(protocol_sha256=sha(ROOT/'protocols/r06_quality_addendum.json'),code_sha256=sha(__file__),
        position_sha256=sha(ROOT/'data/r06_stock_positions.parquet'),mark_sha256=sha(ROOT/'data/r06_stock_mark_quality.parquet'),
        scored_intervals=len(results),endpoint_complete_intervals=int(results.endpoint_complete.sum()),
        mark_rows=len(marks),confirmed_chain_change_rows=int(marks.confirmed_observed_chain_change.sum()),
        median_unknown_endpoint_weight=results.unknown_endpoint_weight.median(),max_unknown_endpoint_weight=results.unknown_endpoint_weight.max(),
        no_imputation=True,not_a_trading_backtest=True))
    print(results.groupby(['era','level'])[['unknown_endpoint_weight','unproven_path_weight','endpoint_complete']].mean().to_string())

if __name__=='__main__':run()
