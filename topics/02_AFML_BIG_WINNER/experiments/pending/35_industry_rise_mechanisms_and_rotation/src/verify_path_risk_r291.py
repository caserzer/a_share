from common import *
import pandas as pd

def run():
    out=ROOT/'outputs/r291';keys=pd.read_parquet(out/'path_keys.parquet');paths=np.load(out/'normalized_paths.npz');stock=paths['stock'];market=paths['market']
    raw=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet');b=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;cal=pd.DatetimeIndex(b.index)
    source={k:g.sort_values('date') for k,g in raw.groupby(KEY)}
    for key,g in keys.groupby(KEY):
        frame=source[key];wanted=cal.to_numpy()[g.day_i.to_numpy()[:,None]+1+np.arange(21)]
        pos=np.searchsorted(frame.date.to_numpy(),wanted);assert (pos<len(frame)).all()
        assert np.array_equal(frame.date.to_numpy()[pos],wanted)
        nav=frame.nav.to_numpy()[pos];bench=b.to_numpy()[g.day_i.to_numpy()[:,None]+1+np.arange(21)]
        assert np.allclose(nav/nav[:,0,None],stock[g.path_id],rtol=0,atol=1e-12)
        assert np.allclose(bench/bench[:,0,None],market[g.path_id],rtol=0,atol=1e-12)
    p=pd.read_parquet(out/'primitive_risks.parquet')
    for (cost,policy),g in p.groupby(['cost','policy']):
        ids=g.path_id.to_numpy();x=stock[ids,1:];y=market[ids,1:]
        worst_hold=np.maximum(0,1-(1-cost)*np.min(x,axis=1));mean_hold=sum(np.maximum(0,1-(1-cost)*x[:,j]) for j in range(20))/20
        if policy=='cash':worst_alt=np.full(len(g),cost);mean_alt=worst_alt;terminal=np.full(len(g),1-cost)
        else:
            worst_alt=np.maximum(0,1-(1-cost)**3*np.min(y,axis=1));mean_alt=sum(np.maximum(0,1-(1-cost)**3*y[:,j]) for j in range(20))/20;terminal=(1-cost)**3*y[:,-1]
        gain=terminal-(1-cost)*x[:,-1]
        for field,values in [('worst_relief',worst_hold-worst_alt),('mean_relief',mean_hold-mean_alt),('missed_positive',np.where(gain<0,-gain,0)),('avoided_negative',np.where(gain>0,gain,0))]:assert np.allclose(values,g[field],rtol=0,atol=1e-12)
    o=pd.read_parquet(ROOT/'outputs/r287/origins.parquet');a=pd.read_parquet(ROOT/'outputs/r287/alerts.parquet');dates=pd.read_parquet(out/'date_metrics.parquet');old=pd.read_parquet(ROOT/'outputs/r290/date_metrics.parquet')
    counts=o.groupby(['era','level','date']).size();choices={k:set(g.industry_code) for k,g in a.groupby(['era','level','date','strategy','variant'])}
    primitives={k:g for k,g in p.groupby(['era','level','date','cost','policy'])}
    for r in dates.itertuples():
        key=(r.era,r.level,r.date);g=primitives[key+(r.cost,r.policy)];n=int(counts.loc[key]);assert len(g)==n
        mask=g.industry_code.isin(choices[key+(r.strategy,r.variant)]).to_numpy();assert mask.sum()==(n+4)//5
        for field in ['worst_relief','mean_relief','missed_positive','avoided_negative']:
            values=g[field].to_numpy();assert np.isclose(np.dot(values,mask)/n,getattr(r,field+'_selected'),atol=1e-12)
            assert np.isclose(values.mean()*((n+4)//5)/n,getattr(r,field+'_random'),atol=1e-12)
    for policy in ['cash','market']:
        q=dates[dates.policy.eq(policy)].merge(old,on=['era','level','date','cost','strategy','variant'],validate='one_to_one');assert q.complete_date.all()
        assert len(q)==old.complete_date.sum()
        for kind in ['selected','random']:assert np.allclose(q['avoided_negative_'+kind]-q['missed_positive_'+kind],q[policy+'_'+kind+'_known_conditional'],atol=1e-12)
    summary=pd.read_csv(out/'summary.csv');fields=[x+'_'+v for x in ['worst_relief','mean_relief','missed_positive','avoided_negative'] for v in ['selected','random']]
    calc=dates.groupby(['era','level','strategy','variant','cost','policy'])[fields].mean().reset_index();q=summary.merge(calc,on=['era','level','strategy','variant','cost','policy'],suffixes=('','_check'),validate='one_to_one')
    assert len(q)==144
    for f in fields:assert np.allclose(q[f],q[f+'_check'])
    pairs=pd.read_csv(out/'regime_comparisons.csv');assert len(pairs)==96
    for field in ['worst_relief_selected','mean_relief_selected','missed_positive_selected','avoided_negative_selected']:assert np.allclose(pairs[field]-pairs[field+'_base'],pairs[field+'_delta'])
    rec=json.loads((out/'receipt.json').read_text())
    for path,h in rec['inputs'].items():assert sha(ROOT/path)==h
    for path,h in rec['outputs'].items():assert sha(out/path)==h
    assert sha(CACHE/'forecast_v5/CSI_ALL.parquet')==rec['benchmark_sha256']
    js(out/'independent_verification.json',dict(status='PASS',path_points=stock.size,primitive_rows=len(p),date_policy_cost_rows=len(dates),groups=len(summary),regime_pairs=len(pairs),verifier_sha256=sha(Path(__file__)),scope='All raw path points, per-industry risk math, equal-weight aggregation and endpoint reconciliation; not portfolio risk certification'))
    print('R291 VERIFIED',stock.size,len(p),len(dates),len(summary))
if __name__=='__main__':run()
