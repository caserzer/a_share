from common import *
import pandas as pd

def run():
    out=ROOT/'outputs/r290';o=pd.read_parquet(ROOT/'outputs/r287/origins.parquet');a=pd.read_parquet(ROOT/'outputs/r287/alerts.parquet');d=pd.read_parquet(out/'date_metrics.parquet');u=pd.read_parquet(out/'unknown_coefficients.parquet')
    raw=pd.read_parquet(ROOT/'outputs/r129/daily_2026-10-21.parquet').set_index(KEY+['date']).nav
    bench=pd.read_parquet(CACHE/'forecast_v5/CSI_ALL.parquet').close;valid=o[o.complete_path]
    entry=valid[KEY].copy();entry['date']=valid.entry_date;end=valid[KEY].copy();end['date']=valid.maturity20
    startnav=raw.reindex(pd.MultiIndex.from_frame(entry)).to_numpy();endnav=raw.reindex(pd.MultiIndex.from_frame(end)).to_numpy()
    actualret=endnav/startnav-1;actualmarket=bench.reindex(valid.maturity20).to_numpy()/bench.reindex(valid.entry_date).to_numpy()-1
    assert np.isfinite(actualret).all() and np.isfinite(actualmarket).all()
    assert np.allclose(actualret,valid.return20,atol=1e-12,rtol=0) and np.allclose(actualmarket,valid.market_return20,atol=1e-12,rtol=0)
    lookup={k:g for k,g in o.groupby(['era','level','date'])}
    selections={k:set(g.industry_code) for k,g in a[a.strategy.isin(['daily','monthly'])].groupby(['era','level','date','strategy','variant'])}
    for r in d.itertuples():
        g=lookup[(r.era,r.level,r.date)];selected=g.industry_code.isin(selections[(r.era,r.level,r.date,r.strategy,r.variant)]).to_numpy();n=len(g);k=int(selected.sum());known=g.complete_path.to_numpy()
        assert k==(n+4)//5 and n==r.eligible and known.sum()==r.known and (~known).sum()==r.unknown and known.all()==r.complete_date
        ret=g.return20.to_numpy()[known];market=g.market_return20.to_numpy()[known];mask=selected[known];p=k/n
        # Explicit terminal cash flow legs, independent of exit_economics.
        held=(1+ret)*(1-r.cost);cash=np.repeat(1-r.cost,len(ret));switched=(1-r.cost)*(1-r.cost)*(1+market)*(1-r.cost)
        for name,payoff in [('cash',cash),('market',switched)]:
            gain=payoff-held
            for kind,weights in [('selected',mask.astype(float)),('random',np.repeat(p,len(ret))),('difference',mask.astype(float)-p)]:
                total=float(np.dot(gain,weights));cond=total/len(ret) if len(ret) else np.nan;contrib=total/n
                assert np.isclose(cond,getattr(r,name+'_'+kind+'_known_conditional'),atol=1e-12,equal_nan=True)
                assert np.isclose(contrib,getattr(r,name+'_'+kind+'_known_contribution'),atol=1e-12)
    for r in u.itertuples():
        g=lookup[(r.era,r.level,r.date)];row=g[g.industry_code.eq(r.industry_code)].iloc[0];selected=r.industry_code in selections[(r.era,r.level,r.date,r.strategy,r.variant)];p=((len(g)+4)//5)/len(g)
        assert not row.complete_path and selected==r.alert and np.isclose((int(selected)-p)/len(g),r.unknown_gain_coefficient)
    summary=pd.read_csv(out/'summary.csv',dtype={'period':str})
    ids=['era','level','strategy','variant','cost']
    for r in summary.itertuples():
        g=d
        for col in ids:g=g[g[col].eq(getattr(r,col))]
        if r.period!='all':g=g[g.date.dt.year.eq(int(r.period))]
        assert len(g)==r.dates and g.complete_date.sum()==r.complete_dates
        for name in ['cash','market']:
            for kind in ['selected','random','difference']:
                col=name+'_'+kind+'_known_conditional'
                assert np.isclose(g.loc[g.complete_date,col].mean(),getattr(r,name+'_'+kind+'_complete'),equal_nan=True)
                assert np.isclose(g[col].mean(),getattr(r,name+'_'+kind+'_conditional'),equal_nan=True)
    rec=json.loads((out/'receipt.json').read_text())
    for p,h in rec['inputs'].items():assert sha(ROOT/p)==h
    for p,h in rec['outputs'].items():assert sha(out/p)==h
    assert sha(CACHE/'forecast_v5/CSI_ALL.parquet')==rec['benchmark_sha256']
    js(out/'independent_verification.json',dict(status='PASS',endpoint_paths=len(valid),date_cost_rows=len(d),unknown_coefficients=len(u),summary_rows=len(summary),verifier_sha256=sha(Path(__file__)),scope='Raw endpoint price and explicit cash-flow validation; overlapping origin experiments, not executable strategy certification'))
    print('R290 VERIFIED',len(valid),len(d),len(u),len(summary))
if __name__=='__main__':run()
