from common import *
import pandas as pd
from scipy.stats import norm

def run():
    out=ROOT/'outputs/r293';raw=pd.read_parquet(out/'paired_dates.parquet');monthly=pd.read_parquet(out/'monthly.parquet');results=pd.read_csv(out/'uncertainty.csv');annual=pd.read_csv(out/'annual.csv');source=pd.read_parquet(ROOT/'outputs/r292/date_metrics.parquet')
    ids=['era','level','strategy','variant','cost','policy'];lookup={k:g.set_index('date') for k,g in source.groupby(ids)}
    definitions={'worst_vs_hold':('hold_worst','model_worst'),'mean_vs_hold':('hold_mean','model_mean'),'worst_vs_random':('random_worst','model_worst'),'mean_vs_random':('random_mean','model_mean')}
    for cid,g in raw.groupby('case_id'):
        ident=tuple(g.iloc[0][k] for k in ids);s=lookup[ident].loc[g.date];name=g.comparison.iloc[0]
        if name in definitions:
            first,second=definitions[name];expected=s[first].to_numpy()-s[second].to_numpy()
        elif name=='terminal_vs_hold':expected=s.terminal_gain.to_numpy()
        else:
            base=list(ident);base[3]='base';b=lookup[tuple(base)].loc[g.date]
            field={'regime_worst':'model_worst','regime_mean':'model_mean','regime_terminal':'terminal_gain'}[name];sign=1 if field=='terminal_gain' else -1;expected=sign*(s[field].to_numpy()-b[field].to_numpy())
        assert np.allclose(expected,g.delta,rtol=0,atol=1e-12)
        expectedvar=s['random_'+name.split('_')[0]+'_mc_variance'].to_numpy() if name.endswith('vs_random') else np.zeros(len(g))
        assert np.allclose(expectedvar,g.mc_variance,rtol=0,atol=1e-16)
    calc=raw.groupby(['case_id','month']).agg(delta=('delta','mean'),dates=('delta','size'),variance=('mc_variance','sum')).reset_index();q=monthly.merge(calc,on=['case_id','month'],suffixes=('','_check'),validate='one_to_one')
    assert np.allclose(q.delta,q.delta_check) and (q.dates==q.dates_check).all() and np.allclose(q.mc_variance,q.variance/q.dates**2)
    planned=pd.read_parquet(ROOT/'outputs/r290/date_metrics.parquet');planned=planned[planned.variant.eq('base')&planned.cost.eq(0)]
    coverage={k:g for k,g in planned.groupby(['era','level','strategy'])};crit=norm.ppf(1-.05/(4*len(results)));assert len(results)==1008
    for r in results.itertuples():
        g=monthly[monthly.case_id.eq(r.case_id)].sort_values('month');n=len(g);months=pd.PeriodIndex(g.month,freq='M');x=g.delta.to_numpy();u=x-x.mean();distance=np.abs(months.asi8[:,None]-months.asi8[None,:]);kernel=np.clip(1-distance/7,0,1);se=np.sqrt(max(float(u@kernel@u),0))/n;mc=np.sqrt(g.mc_variance.sum())/n
        assert np.isclose(x.mean(),r.mean) and np.isclose(np.average(x,weights=g.dates),r.date_weighted_mean)
        assert np.isclose(se,r.historical_hac_se,rtol=1e-10,atol=1e-14) and np.isclose(mc,r.mc_se,rtol=1e-10,atol=1e-14)
        years=g.assign(year=months.year).groupby('year').delta.mean();pa=coverage[(r.era,r.level,r.strategy)];complete=bool(pa.complete_date.all());eligible=n>=24 and len(years)>=3 and se>1e-15 and complete
        assert complete==r.whole_pair and len(pa)==r.planned_dates and (~pa.complete_date).sum()==r.incomplete_dates
        assert eligible==r.eligible and n==r.months and len(years)==r.years and years.gt(0).sum()==r.positive_years and years.lt(0).sum()==r.negative_years
        if not eligible:assert pd.isna(r.adjusted_low) and pd.isna(r.adjusted_high) and not r.stable_support
        else:assert np.isclose(r.adjusted_low,x.mean()-crit*(se+mc)) and np.isclose(r.adjusted_high,x.mean()+crit*(se+mc))
        for y,value in years.items():
            row=annual[annual.case_id.eq(r.case_id)&annual.year.eq(y)];assert len(row)==1 and np.isclose(row.iloc[0]['mean'],value) and row.iloc[0].months==sum(months.year==y)
    rec=json.loads((out/'receipt.json').read_text())
    for p,h in rec['inputs'].items():assert sha(ROOT/p)==h
    for p,h in rec['outputs'].items():assert sha(out/p)==h
    js(out/'independent_verification.json',dict(status='PASS',paired_dates=len(raw),monthly_rows=len(monthly),cases=len(results),annual_rows=len(annual),eligible=int(results.eligible.sum()),verifier_sha256=sha(Path(__file__)),scope='Original date contrasts, matrix HAC, calendar-month/annual aggregation, separate MC error and unchanged gates; no stable predictive certification'))
    print('R293 VERIFIED',len(raw),len(monthly),len(results),len(annual))
if __name__=='__main__':run()
